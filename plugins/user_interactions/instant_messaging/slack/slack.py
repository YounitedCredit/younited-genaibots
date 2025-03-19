import asyncio
import copy
import hashlib
import hmac
import json
import time
import traceback
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import parse_qs

import aiohttp
from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from utils.plugin_manager.plugin_manager import PluginManager

from .utils.slack_input_handler import SlackInputHandler
from .utils.slack_output_handler import SlackOutputHandler
from .utils.slack_reactions import SlackReactions


class SlackConfig(BaseModel):
    PLUGIN_NAME: str
    SLACK_ROUTE_PATH: str
    SLACK_ROUTE_METHODS: List[str]
    SLACK_PLUGIN_DIRECTORY: str
    SLACK_MESSAGE_TTL: int
    SLACK_SIGNING_SECRET: str
    SLACK_BOT_TOKEN: str
    SLACK_BOT_USER_TOKEN: str
    SLACK_BOT_USER_ID: str
    SLACK_API_URL: str
    SLACK_AUTHORIZED_CHANNELS: str
    SLACK_AUTHORIZED_APPS: str
    SLACK_AUTHORIZED_WEBHOOKS: str
    SLACK_FEEDBACK_CHANNEL: str
    SLACK_FEEDBACK_BOT_ID: str
    SLACK_MAX_MESSAGE_LENGTH: int
    SLACK_INTERNAL_CHANNEL: str
    SLACK_WORKSPACE_NAME: str
    SLACK_BEHAVIOR_PLUGIN_NAME: str
    SLACK_AUTHORIZE_DIRECT_MESSAGE: bool

class SlackReactionsConfig(BaseModel):
    PROCESSING: str
    DONE: str
    ACKNOWLEDGE: str
    GENERATING: str
    WRITING: str
    ERROR: str
    WAIT: str


class SlackPlugin(UserInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager: GlobalManager = global_manager
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        self.logger = global_manager.logger
        self.plugin_configs = global_manager.config_manager.config_model.PLUGINS
        config_dict = global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.INSTANT_MESSAGING["SLACK"]
        config_dict_reaction = global_manager.config_manager.config_model.UTILS.INSTANT_MESSAGING_REACTIONS["SLACK"]
        self.slack_config = SlackConfig(**config_dict)
        self._reactions = SlackReactionsConfig(**config_dict_reaction)
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None
        

    @property
    def route_path(self):
        return self._route_path

    @property
    def route_methods(self):
        return self._route_methods

    @property
    def reactions(self):
        return self._reactions

    @property
    def plugin_name(self):
        return "slack"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def initialize(self):
        self.slack_input_handler = SlackInputHandler(self.global_manager, self.slack_config)
        self.slack_output_handler = SlackOutputHandler(self.global_manager, self.slack_config)

        self.SLACK_MESSAGE_TTL = self.slack_config.SLACK_MESSAGE_TTL
        self.SLACK_AUTHORIZED_CHANNELS = self.slack_config.SLACK_AUTHORIZED_CHANNELS.split(",")
        self.SLACK_AUTHORIZED_APPS = self.slack_config.SLACK_AUTHORIZED_APPS.split(",")
        self.SLACK_AUTHORIZED_WEBHOOKS = self.slack_config.SLACK_AUTHORIZED_WEBHOOKS.split(",")
        self.SLACK_FEEDBACK_CHANNEL = self.slack_config.SLACK_FEEDBACK_CHANNEL
        self.slack_bot_token = self.slack_config.SLACK_BOT_TOKEN
        self.slack_signing_secret = self.slack_config.SLACK_SIGNING_SECRET
        self._route_path = self.slack_config.SLACK_ROUTE_PATH
        self._route_methods = self.slack_config.SLACK_ROUTE_METHODS
        self.bot_user_id = self.slack_config.SLACK_BOT_USER_ID
        self.MAX_MESSAGE_LENGTH = self.slack_config.SLACK_MAX_MESSAGE_LENGTH
        self.INTERNAL_CHANNEL = self.slack_config.SLACK_INTERNAL_CHANNEL
        self.WORKSPACE_NAME = self.slack_config.SLACK_WORKSPACE_NAME
        self.plugin_name = self.slack_config.PLUGIN_NAME
        self.FEEDBACK_BOT_USER_ID = self.slack_config.SLACK_FEEDBACK_BOT_ID
        self.SLACK_AUTHORIZE_DIRECT_MESSAGE = self.slack_config.SLACK_AUTHORIZE_DIRECT_MESSAGE
        # Dispatchers
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def handle_request(self, request: Request):
        try:
            self.logger.debug(f"request received: {request}")
            response = Response("OK", status_code=200)
            raw_body = await request.body()
            raw_body_str = raw_body.decode('utf-8')  # Decode bytes to string

            # Check if the request is a slash command
            if request.headers['content-type'] == 'application/x-www-form-urlencoded':
                asyncio.create_task(self.execute_slash_command(request, raw_body_str))
            else:
                event_data = json.loads(raw_body_str)  # Parse JSON from string

                # The challenge/response mechanism is used to verify the server's identity by Slack API.
                # When the server receives a challenge request, it must quickly respond with the challenge value.
                # This is important for initializing event notifications with the Slack API.
                if 'challenge' in event_data:
                    challenge = event_data['challenge']
                    self.logger.info(f"Challenge received: {challenge}")
                    return Response(content=challenge, status_code=200, media_type="text/plain")

                headers = request.headers
                self.logger.info(f"Request received from <{request.url.path}>")
                # Create a new task to handle the rest of the processing
                asyncio.create_task(self.process_event_data(event_data, headers, raw_body_str))

            return response

        except Exception as e:
            self.logger.error(f"Error processing request from <{request.headers.get('Referer')}>: {e}")
            return response

    async def execute_slash_command(self, request: Request, raw_body_str):
        self.logger.debug("Validating request...")
        headers = request.headers
        self.root_message_timestamp = headers.get('X-Slack-Request-Timestamp')
        slack_signature = headers.get('X-Slack-Signature')
        event_data = parse_qs(raw_body_str)

        if slack_signature is None:
            self.logger.error("Slack signature not found in headers.")

        # Extract the command from the event data
        command = event_data.get('command', [''])[0]
        channel_id = event_data.get('channel_id', [''])[0]

        # Check if the command is 'list'
        if command == '/listprompt':
            files = await self.backend_internal_data_processing_dispatcher.list_container_files(
                self.backend_internal_data_processing_dispatcher.prompts)
            if files is None:
                self.logger.error("Error listing prompt files.")
                return
            else:
                files = [f"{file}\n" for file in files if file not in [self.global_manager.bot_config.MAIN_PROMPT,
                                                                       self.global_manager.bot_config.CORE_PROMPT]]
                files = ''.join(files)
                await self.slack_output_handler.send_slack_message(channel_id=channel_id, response_id=None,
                                                                   message=files, message_type=MessageType.TEXT)
        elif command == '/setprompt':
            try:
                prompt_name = event_data.get('text', [''])[0]
                prompt_folder = self.backend_internal_data_processing_dispatcher.prompts
                main_prompt_name = self.global_manager.bot_config.MAIN_PROMPT
                prompt_text = await self.backend_internal_data_processing_dispatcher.read_data_content(prompt_folder,
                                                                                                       f"{prompt_name}.txt")
                await self.backend_internal_data_processing_dispatcher.write_data_content(data_container=prompt_folder,
                                                                                          data_file=f"{main_prompt_name}.txt",
                                                                                          data=prompt_text)
                await self.slack_output_handler.send_slack_message(channel_id=channel_id, response_id=None,
                                                                   message=f"Main prompt updated successfully to [{prompt_name}].",
                                                                   message_type=MessageType.COMMENT)
            except IndexError:
                self.logger.error("No text found in event data.")
                return
            except Exception as e:
                self.logger.error(f"Error extracting text from event data: {e}")
                return

    async def process_event_data(self, event_data, headers, raw_body_str):
        try:
            if await self.validate_request(event_data, headers, raw_body_str):
                await self.handle_valid_request(event_data)
            else:
                self.logger.debug("Request discarded")
        except Exception as e:
            self.logger.error(f"An error occurred while processing user input: {e}\n{traceback.format_exc()}")

    async def handle_valid_request(self, event_data):
        try:
            user_id = event_data.get('event', {}).get('user')
            app_id = event_data.get('event', {}).get('app_id')
            api_app_id = event_data.get('api_app_id')
            channel_id = event_data.get('event', {}).get('channel')
            if user_id is not None:
                self.logger.info(
                    f"Valid <SLACK> request received from user {user_id} in channel {channel_id}, processing..")
            if app_id is not None:
                self.logger.info(
                    f"Valid <SLACK> request received from app {app_id} in channel {channel_id}, processing..")
            event_type = event_data.get('event', {}).get('type')
            event_subtype = event_data.get('event', {}).get('subtype')

            await self.process_event_by_type(event_data, event_type, event_subtype)
        except Exception as e:
            self.logger.error(f"An error occurred while processing user input: {e}")
            raise

    async def process_event_by_type(self, event_data, event_type, event_subtype):
        if event_type == 'message' and (event_subtype is None or event_subtype == "bot_message"):
            await self.process_interaction(event_data)
        elif event_subtype == "file_share":
            await self.process_interaction(event_data)
        elif event_subtype is not None:
            self.logger.info(f"ignoring channel event subtype: {event_subtype}")
        else:
            self.logger.debug(f"Event type is not 'message', it's '{event_type}'. Skipping processing.")

    async def process_interaction(self, event_data):
        await self.global_manager.user_interactions_behavior_dispatcher.process_interaction(
            event_data=event_data,
            event_origin=self.plugin_name,
            plugin_name=self.slack_config.SLACK_BEHAVIOR_PLUGIN_NAME
        )

    async def validate_request(self, event_data=None, headers=None, raw_body_str=None):
        self.logger.debug("Validating request...")
        if not self._validate_headers(headers):
            return False

        event = event_data.get('event', {})
        event_type = event.get('type')
        ts = event.get('event_ts')
        channel_id = event.get('channel') or event.get('channel_id')
        user_id = event_data.get('event', {}).get('user', None)
        api_app_id = event_data.get('api_app_id', None)
        app_id = event_data.get('event', {}).get('app_id', None)
        self.logger.debug(f"event_type: {event_type}, ts: {ts}")
        if not self._validate_signature(headers, raw_body_str):
            return False

        if not self._validate_event_data(event_type, ts, channel_id, user_id, app_id, api_app_id, event):
            return False

        if not await self._validate_processing_status(channel_id, ts):
            return False

        self.logger.info("Request validated successfully.")
        return True

    def _validate_headers(self, headers):
        self.root_message_timestamp = headers.get('X-Slack-Request-Timestamp')
        slack_signature = headers.get('X-Slack-Signature')
        if slack_signature is None:
            self.logger.error("Slack signature not found in headers.")
            return False
        if not self.slack_signing_secret:
            self.logger.error("Slack signing secret not found.")
            return False
        return True

    def _validate_signature(self, headers, raw_body_str):
        slack_signature = headers.get('X-Slack-Signature')
        sig_basestring = f'v0:{self.root_message_timestamp}:{raw_body_str}'
        my_signature = 'v0=' + hmac.new(
            self.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(my_signature, slack_signature):
            self.logger.error("Discarding request: Computed signature does not match Slack signature.")
            return False
        return True

    def _validate_event_data(self, event_type, ts, channel_id, user_id, app_id, api_app_id, event):
        if (user_id is None and app_id is None and api_app_id is None) or channel_id is None:
            self.logger.debug(
                f"User ID is {'None' if user_id is None else 'set'}, App ID is {'None' if app_id is None else 'set'}, API App ID is {'None' if app_id is None else 'set'}, Channel ID is {'None' if channel_id is None else 'set'}")
            return False

        if event_type == "reaction_added":
            self.logger.info("Discarding request: ignoring emoji reaction notification")
            return False

        if event.get('user') == self.bot_user_id:
            self.logger.info("Discarding request: message from the bot itself")
            return False

        if ((api_app_id is not None and user_id is not None and app_id is not None) or (
                api_app_id is not None and app_id is None)):
            if api_app_id not in self.SLACK_AUTHORIZED_WEBHOOKS and api_app_id != self.bot_user_id:
                self.logger.info(f"Discarding request: ignoring event from unauthorized webhook: {api_app_id}")
                return False

        if app_id is not None and api_app_id is None:
            if app_id not in self.SLACK_AUTHORIZED_APPS and app_id != self.bot_user_id:
                self.logger.info(f"Discarding request: ignoring event from unauthorized app: {app_id}")
                return False

        if channel_id.startswith('D'):
            if not self.SLACK_AUTHORIZE_DIRECT_MESSAGE:
                self.logger.info(f"Discarding request: ignoring direct message from unauthorized channel: {channel_id}")
                return False
        else:
            if channel_id not in self.SLACK_AUTHORIZED_CHANNELS and channel_id != self.SLACK_FEEDBACK_CHANNEL:
                self.logger.info(f"Discarding request: ignoring event from unauthorized channel: {channel_id}")
                return False

        if channel_id == self.SLACK_FEEDBACK_CHANNEL and user_id != self.FEEDBACK_BOT_USER_ID:
            self.logger.info(
                f"Discarding request: ignoring event from unauthorized user in feedback channel: {user_id}")
            return False

        if event_type not in ['message', 'app_mention', 'file_shared']:
            self.logger.info("Event type is not 'message', 'file_shared' or 'app_mention'.")
            return False

        return True

    async def _validate_processing_status(self, channel_id, ts):
        if await self.is_message_too_old(ts):
            self.logger.info("Discarding request: old message notification")
            return False

        session_name = f"{channel_id}-{ts}.txt"
        processing_container = self.backend_internal_data_processing_dispatcher.processing
        result = await self.backend_internal_data_processing_dispatcher.read_data_content(processing_container,
                                                                                          session_name)

        if result is not None:
            self.logger.warning(f"Discarding request: This request is already being processed for {session_name}")
            return False

        return True

    async def request_to_notification_data(self, event_data):
        incoming_data: IncomingNotificationDataBase = await self.slack_input_handler.request_to_notification_data(
            event_data)
        return incoming_data

    def split_message(self, message, length):
        if message is None:
            return []
        message_blocks = []
        while message:
            if len(message) > length:
                split_index = message.rfind('\n', 0, length)
                if split_index == -1:  # No newline character in the first 'length' characters
                    split_index = length
                message_block = message[:split_index]
                message = message[split_index:].lstrip('\n')
            else:
                message_block = message
                message = ''
            message_blocks.append(message_block)
        return message_blocks

    async def send_message(self, message, event: IncomingNotificationDataBase, message_type=MessageType.TEXT,
                           title=None, is_internal=False, show_ref=False):
        try:
            if not isinstance(message_type, MessageType):
                raise ValueError(f"Invalid message type: {message_type}. Expected MessageType enum.")

            headers = {'Authorization': f'Bearer {self.slack_bot_token}'}
            event_copy = copy.deepcopy(event)
            channel_id = event_copy.channel_id
            response_id = event_copy.response_id

            try:
                # Example of asynchronous search
                already_found_internal_ts = await self.slack_input_handler.search_message_in_thread(
                    query=f"thread: {event.channel_id}-{response_id}"
                )
            except Exception as e:
                self.logger.error(f"Error searching message in thread: {str(e)}")
                return

            message_blocks = self.split_message(message, self.MAX_MESSAGE_LENGTH) if message else []

            try:
                if show_ref:
                    is_new_message_added = await self.add_reference_message(event, message_blocks, response_id)
                else:
                    is_new_message_added = False
            except Exception as e:
                self.logger.error(f"Error adding reference message: {str(e)}")
                return

            try:
                if is_internal:
                    response_id, channel_id = await self.handle_internal_message(
                        event, event_copy, response_id, already_found_internal_ts, show_ref
                    )
            except Exception as e:
                self.logger.error(f"Error handling internal message: {str(e)}")
                return

            await self.global_manager.user_interactions_behavior_dispatcher.begin_wait_backend(
                event, event.channel_id, event.timestamp
            )

            async with aiohttp.ClientSession() as session:  # Asynchronous HTTP session
                for i, message_block in enumerate(message_blocks):
                    try:
                        await self.global_manager.user_interactions_behavior_dispatcher.end_wait_backend(
                            event=event, channel_id=event.channel_id, timestamp=event.timestamp
                        )
                        payload = self.construct_payload(
                            channel_id, response_id, message_block, message_type, i, len(message_blocks), title,
                            is_new_message_added
                        )

                        async with session.post(
                                'https://slack.com/api/chat.postMessage',
                                headers=headers,
                                json=payload
                        ) as response:
                            if response.status != 200:
                                self.logger.error(f"Error sending message to Slack: {response.status}")
                            else:
                                result = await response.json()  # Wait for the async response body

                            self.handle_response(result, message_block)

                        if i == 0 and is_new_message_added:
                            is_new_message_added = False

                    except Exception as e:
                        self.logger.error(f"Exception occurred while sending message block to Slack: {str(e)}")

            if response:
                return result
            else:
                self.logger.error("Empty response received from Slack")
                return None

        except Exception as e:
            self.logger.error(f"Exception occurred in send_message: {str(e)}")
            self.global_manager.user_interactions_dispatcher.send_message(event=event,
                                                                          message=f"An error occured while sending a message from slack plugin: {str(e)}",
                                                                          message_type=MessageType.COMMENT,
                                                                          is_internal=True)
            return None

    async def add_reference_message(self, event, message_blocks, response_id):
        msg_url, msg_text = await self.slack_input_handler.get_message_permalink_and_text(event.channel_id,
                                                                                          event.timestamp)
        if msg_url and msg_text:
            reference_message = f"<{msg_url}|[ref msg link]> | thread: `{event.channel_id}-{response_id}`"
            message_blocks.insert(0, reference_message)
            return True
        return False

    async def handle_internal_message(self, event, event_copy: IncomingNotificationDataBase, response_id,
                                      already_found_internal_ts, show_ref):
        try:
            if self.INTERNAL_CHANNEL is None:
                self.logger.warning(
                    "An internal message was sent but INTERNAL_CHANNEL is not defined, so the message is sent in the original thread.")
                return response_id, event.channel_id

            event_copy.channel_id = self.INTERNAL_CHANNEL
            if already_found_internal_ts:
                return already_found_internal_ts, self.INTERNAL_CHANNEL

            if not show_ref:
                search_internal_ts = None
                start_time = time.time()
                attempt = 1
                delay = 1  # Start with a 1-second delay for the exponential backoff

                self.logger.info("Waiting for internal message to be posted...")

                # Keep trying until message is found or timeout of 40 seconds
                while search_internal_ts is None and time.time() - start_time <= 40:
                    self.logger.info(f"Attempt {attempt}: waiting for internal message to be posted...")

                    try:
                        # Search for the message
                        search_internal_ts = await self.slack_input_handler.search_message_in_thread(
                            query=f"thread: {event.channel_id}-{response_id}")

                        # If found, break out of the loop
                        if search_internal_ts:
                            response_id = search_internal_ts
                            self.logger.info(f"Internal message found with timestamp {search_internal_ts}")
                        else:
                            self.logger.info(f"Message not found, retrying in {delay} seconds...")
                            await asyncio.sleep(delay)  # Sleep for 'delay' seconds
                            delay = min(delay * 1.5, 9)  # Exponential backoff: increase delay (max 8 seconds)
                        attempt += 1
                    except Exception as e:
                        self.logger.error(f"Error searching for internal message: {str(e)}")
                        await self.global_manager.user_interactions_dispatcher.send_message(
                            event=event,
                            message=f"An error occurred while searching for an internal message: {str(e)}",
                            message_type=MessageType.COMMENT,
                            is_internal=True
                        )
                        return response_id, event.channel_id

                # If we didn't find the message within 40 seconds, fall back to the original thread
                if search_internal_ts is None:
                    self.logger.warning(
                        "Internal message not found after 40 seconds, sending the message in the original thread.")
                else:
                    event_copy.thread_id = search_internal_ts

            return response_id, self.INTERNAL_CHANNEL

        except Exception as e:
            self.logger.error(f"Exception occurred in handle_internal_message: {str(e)}")
            await self.global_manager.user_interactions_dispatcher.send_message(
                event=event,
                message=f"An error occurred in handle_internal_message: {str(e)}",
                message_type=MessageType.COMMENT,
                is_internal=True
            )
            return response_id, event.channel_id

    def construct_payload(self, channel_id, response_id, message_block, message_type, block_index, total_blocks, title,
                          is_new_message_added):
        payload = {
            'channel': channel_id,
            'thread_ts': response_id
        }

        if block_index == 0 and is_new_message_added:
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message_block}}]
            payload['blocks'] = json.dumps(blocks)
        elif message_type.value == "text":
            if block_index < total_blocks - 1:
                message_block += '...'
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message_block}}]
            payload['blocks'] = json.dumps(blocks)
        elif MessageType.has_value(message_type.value):
            blocks = self.slack_output_handler.format_slack_message(title, message_block, message_format=message_type)
            payload['blocks'] = json.dumps(blocks)
        else:
            raise ValueError(f"Invalid message type. Use {', '.join([e.value for e in MessageType])}.")

        return payload

    def handle_response(self, response, message_block):
        # Check if the response is already a dictionary
        if isinstance(response, dict):
            response_data = response  # Use it directly
        else:
            # If it's a string or an HTTP response, parse it as JSON
            response_data = json.loads(response.text)

        # Further process the response_data as needed...
        if not response_data.get('ok'):
            error_message = response_data.get('error')
            detailed_errors = response_data.get('errors')
            self.logger.error(
                f"Error posting message to Slack: {error_message}. Detailed errors: {detailed_errors}. Original message: \n{message_block}")

    def split_message(self, message, length):
        if message is None:
            return []
        message_blocks = []
        while message:
            if len(message) > length:
                split_index = message.rfind('\n', 0, length)
                if split_index == -1:
                    split_index = length
                message_block = message[:split_index]
                message = message[split_index:].lstrip('\n')
            else:
                message_block = message
                message = ''
            message_blocks.append(message_block)
        return message_blocks

    async def upload_file(self, event: IncomingNotificationDataBase, file_content, filename, title, is_internal=False):
        event_copy = copy.deepcopy(event)
        if is_internal:
            await self.handle_internal_channel(event, event_copy)
        await self.slack_output_handler.upload_file_to_slack(event=event_copy, file_content=file_content,
                                                             filename=filename, title=title)

    async def handle_internal_channel(self, event, event_copy):
        if self.INTERNAL_CHANNEL is None:
            self.logger.warning(
                "An internal message was sent but INTERNAL_CHANNEL is not defined, so the message is sent in the original thread.")
        else:
            event_copy.channel_id = self.INTERNAL_CHANNEL
            await self.wait_for_internal_message(event, event_copy)

    async def wait_for_internal_message(self, event, event_copy):
        try:
            start_time = time.time()
            attempt = 1  # Initialize attempt counter
            search_internal_ts = None

            while search_internal_ts is None and time.time() - start_time <= 15:
                self.logger.info(f"Attempt {attempt}: waiting for internal file object to be posted...")
                try:
                    search_internal_ts = await self.slack_input_handler.search_message_in_thread(
                        query=f"thread: {event.channel_id}-{event.response_id}")
                    if search_internal_ts:  # If a message was found in the internal thread
                        event_copy.thread_id = search_internal_ts
                    else:
                        await asyncio.sleep(3)  # Wait for 3 seconds before trying again
                    attempt += 1  # Increment attempt counter
                except Exception as e:
                    self.logger.error(f"Error searching for internal message in wait_for_internal_message: {str(e)}")
                    await self.global_manager.user_interactions_dispatcher.send_message(
                        event=event,
                        message=f"An error occurred while searching for an internal message in wait_for_internal_message: {str(e)}",
                        message_type=MessageType.COMMENT,
                        is_internal=True
                    )
                    return

            if search_internal_ts is None:
                self.logger.warning(
                    "Internal message not found after 15 seconds, sending the message in the original thread.")
            else:
                self.logger.info(f"Internal thread found: {search_internal_ts}")
                event_copy.thread_id = search_internal_ts

        except Exception as e:
            self.logger.error(f"Exception occurred in wait_for_internal_message: {str(e)}")
            await self.global_manager.user_interactions_dispatcher.send_message(
                event=event,
                message=f"An error occurred in wait_for_internal_message: {str(e)}",
                message_type=MessageType.COMMENT,
                is_internal=True
            )

    async def add_reaction(self, event, channel_id, timestamp, reaction_name):
        missing = [var for var, value in locals().items() if value is None]
        if missing:
            self.logger.debug('The following variables are empty: %s', ', '.join(missing))
        else:
            await self.slack_output_handler.add_reaction(channel_id, timestamp, reaction_name)

    async def remove_reaction(self, event, channel_id, timestamp, reaction_name):
        missing = [var for var, value in locals().items() if value is None]
        if missing:
            self.logger.debug('The following variables are empty: %s', ', '.join(missing))
        else:
            await self.slack_output_handler.remove_reaction(channel_id, timestamp, reaction_name)

    async def is_message_too_old(self, event_ts):
        event_ts = datetime.fromtimestamp(float(event_ts.split('.')[0]), timezone.utc)
        # Convertir le timestamp de l'événement en objet datetime
        event_datetime = event_ts
        # Obtenir le datetime actuel
        current_datetime = datetime.now(timezone.utc)
        # Calculer la différence
        diff = current_datetime - event_datetime
        return diff.total_seconds() > self.SLACK_MESSAGE_TTL

    def format_trigger_genai_message(self, message):
        bot_id = self.bot_user_id
        formatted_message = f"<@{bot_id}> {message}"
        return formatted_message

    async def fetch_conversation_history(
            self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        """
        Fetch the conversation history via SlackOutputHandler.
        If channel_id and thread_id are provided, they will be used instead of the event's channel and thread IDs.
        """
        try:
            # Use provided channel_id and thread_id, or fallback to the event values
            final_channel_id = channel_id if channel_id else event.channel_id
            final_thread_id = thread_id if thread_id else event.thread_id

            # Use SlackOutputHandler to fetch conversation history
            messages = await self.slack_output_handler.fetch_conversation_history(channel_id=final_channel_id,
                                                                                  thread_id=final_thread_id)

            # Convert each message into IncomingNotificationDataBase
            event_data_list = []
            for message in messages:
                # Convert each Slack message into an IncomingNotificationDataBase object
                event_data = await self.request_to_notification_data({"event": message})
                if event_data and event_data.timestamp != event.timestamp and event_data.user_id != self.bot_user_id:
                    event_data_list.append(event_data)

            # Log the number of events found
            self.logger.info(f"Fetched {len(event_data_list)} events from the conversation history.")

            return event_data_list
        except Exception as e:
            self.logger.error(f"Error fetching conversation history: {e}")
            return []

    async def remove_reaction_from_thread(self, channel_id, thread_id, reaction_name):
        try:
            await self.slack_output_handler.remove_reaction_from_thread(channel_id, thread_id, reaction_name)
        except Exception as e:
            self.logger.error(f"Error removing reaction: {e} in Slack Output Handler remove_reaction")

    def get_bot_id(self) -> str:
        return self.slack_config.SLACK_BOT_USER_ID
