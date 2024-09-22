import asyncio
import base64
import json
from datetime import datetime
from typing import List, Optional

import requests
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity
from botframework.connector import ConnectorClient
from botframework.connector.auth import (
    ChannelValidation,
    MicrosoftAppCredentials,
    SimpleCredentialProvider,
)
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
from plugins.user_interactions.instant_messaging.teams.bots import TeamsConversationBot
from plugins.user_interactions.instant_messaging.teams.utils.teams_event_data import (
    TeamsEventData,
)
from utils.logging.logger_loader import logging
from utils.plugin_manager.plugin_manager import PluginManager

from .utils.teams_reactions import TeamsReactions


class TeamsConfig(BaseModel):
    PLUGIN_NAME: str
    TEAMS_APP_ID: str
    TEAMS_APP_PASSWORD: str
    ROUTE_PATH: str
    ROUTE_METHODS: List[str]
    TEAMS_BOT_USER_ID : str
    TEAMS_AUTHORIZED_CHANNELS : str
    TEAMS_FEEDBACK_CHANNEL : str
    TEAMS_FEEDBACK_BOT_USER_ID : str
    BEHAVIOR_PLUGIN_NAME: str

class TeamsPlugin(UserInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager :GlobalManager = global_manager
        self.plugin_manager :PluginManager = global_manager.plugin_manager
        self.logger = global_manager.logger
        self.plugin_configs = global_manager.config_manager.config_model.PLUGINS
        self._reactions = TeamsReactions()
        config_dict = global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.INSTANT_MESSAGING["TEAMS"]
        self.teams_config = TeamsConfig(**config_dict)
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None
        self.APPJSON = "application/json"

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
        return "teams"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def initialize(self):

        # Dispatchers
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self._route_path = self.teams_config.ROUTE_PATH
        self._route_methods = self.teams_config.ROUTE_METHODS
        self.bot_user_id = self.teams_config.TEAMS_BOT_USER_ID
        self.teams_authorized_channels = self.teams_config.TEAMS_AUTHORIZED_CHANNELS.split(',')
        self.teams_feedback_channel = self.teams_config.TEAMS_FEEDBACK_CHANNEL
        self.teams_feedback_bot_user_id = self.teams_config.TEAMS_FEEDBACK_BOT_USER_ID
        self.settings = BotFrameworkAdapterSettings(self.teams_config.TEAMS_APP_ID, self.teams_config.TEAMS_APP_PASSWORD)
        self.adapter = BotFrameworkAdapter(self.settings)
        self.credentials = MicrosoftAppCredentials(self.teams_config.TEAMS_APP_ID, self.teams_config.TEAMS_APP_PASSWORD)
        self.BOT = TeamsConversationBot(self.teams_config.TEAMS_APP_ID, self.teams_config.TEAMS_APP_PASSWORD)

    async def handle_request(self, request: Request):
        try:
            self.logger.debug(f"request received: {request}")
            raw_body = await request.body()
            raw_body_str = raw_body.decode('utf-8')
            event_data = json.loads(raw_body_str)
            raw_request = await request.json()

            self.body = raw_request
            self.headers = request.headers
            self.activity = Activity().deserialize(self.body)

            self.logger.info(f"Request received from <{request.url.path}>")

            # Create a new task to handle the rest of the processing
            asyncio.create_task(self.process_event_data(event_data, self.headers, raw_request))

            return Response(
                content=json.dumps({"status": "success", "message": "Request accepted for processing"}),
                media_type= self.APPJSON,
                status_code=202  # 202 Accepted
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in request: {e}")
            return Response(
                content=json.dumps({"status": "error", "message": "Invalid JSON in request"}),
                media_type=self.APPJSON,
                status_code=400  # 400 Bad Request
            )

        except Exception as e:
            self.logger.error(f"Error processing request from <{request.headers.get('Referer')}>: {e}")
            return Response(
                content=json.dumps({"status": "error", "message": "Internal server error"}),
                media_type=self.APPJSON,
                status_code=500  # 500 Internal Server Error
            )

    async def process_event_data(self, event_data, headers, request_json):
        try:
            validate_request = await self.validate_request(event_data, headers, request_json)

            if validate_request == True:
                try:
                    user_id = event_data.get('from', {}).get('aadObjectId')
                    channel_type = event_data.get('conversation').get('conversationType')
                    if channel_type != 'personal':
                        channel_id = event_data.get('channelData').get('teamsChannelId')
                    else:
                        channel_id = f"personal_{user_id}"


                    self.logger.info(f"Valid <TEAMS> request received from user {user_id} in channel {channel_id}, processing..")
                    event_type = event_data.get('type')

                    if event_type == 'message':
                        await self.global_manager.user_interactions_behavior_dispatcher.process_interaction(
                            event_data=event_data,
                            event_origin= self.plugin_name,
                            plugin_name=self.teams_config.BEHAVIOR_PLUGIN_NAME
                        )
                    else:
                        self.logger.debug(f"Event type is not 'message', it's '{event_type}'. Skipping processing.")
                except Exception as e:
                    logging.error(f"An error occurred while processing user input: {e}")
                    raise
            else:
                self.logger.debug("Request discarded")
        except Exception as e:
            self.logger.error(f"An error occurred while processing user input: {e}")
            raise  # re-raise the exception

    async def validate_request(self, event_data = None, headers = None, raw_body_str = None):
        self.logger.debug("Validating request...")

        if not await self._validate_auth_header(headers):
            return False

        if not await self._authenticate_token(event_data, headers):
            return False

        user_id, channel_id, channel_type = self._extract_user_and_channel_info(event_data)

        if not self._validate_user_and_channel(user_id, channel_id, channel_type):
            return False

        event_type = event_data.get('type')
        if event_type not in ['message']:
            self.logger.info("Event type is not 'message'.")
            return False

        if await self._is_duplicate_request(event_data, user_id, channel_id, channel_type):
            return False

        self.logger.info("Request validated successfully.")
        return True

    async def _validate_auth_header(self, headers):
        auth_header = headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            self.logger.error("Authorization header is not valid.")
            return False
        return True

    async def _authenticate_token(self, event_data, headers):
        credentials = SimpleCredentialProvider(self.teams_config.TEAMS_APP_ID, self.teams_config.TEAMS_APP_PASSWORD)
        auth_header = headers.get("Authorization")
        token = auth_header.split(' ')[1]
        teams_bot_channel = event_data.get('channelId')
        service_url = event_data.get('serviceUrl')

        try:
            authenth = await ChannelValidation.authenticate_channel_token_with_service_url(
                auth_header, credentials, service_url, teams_bot_channel)
            if not authenth.is_authenticated:
                self.logger.info("Discarding request: invalid authentication from request author.")
                return False
        except Exception as e:
            self.logger.error(f"Token validation failed: {str(e)}")
            return False
        return True

    def _extract_user_and_channel_info(self, event_data):
        user_id = event_data.get('from', {}).get('aadObjectId')
        channel_type = event_data.get('conversation', {}).get('conversationType')
        channel_id = event_data.get('channelData', {}).get('teamsChannelId') if channel_type != 'personal' else None
        return user_id, channel_id, channel_type

    def _validate_user_and_channel(self, user_id, channel_id, channel_type):
        if channel_type != 'personal' and (user_id is None or channel_id is None):
            self.logger.debug(f"User ID is {'None' if user_id is None else 'set'}, Channel ID is {'None' if channel_id is None else 'set'}")
            return False

        if user_id == self.bot_user_id:
            self.logger.info("Discarding request: message from the bot itself")
            return False

        if channel_id not in self.teams_authorized_channels and channel_id != self.teams_feedback_channel and channel_type != 'personal':
            self.logger.info(f"Discarding request: ignoring event from unauthorized channel: {channel_id}")
            return False

        if channel_id == self.teams_feedback_channel and user_id != self.teams_feedback_bot_user_id:
            self.logger.info(f"Discarding request: ignoring event from unauthorized user in feedback channel: {user_id}")
            return False

        return True

    async def _is_duplicate_request(self, event_data, user_id, channel_id, channel_type):
        if channel_type != 'personal':
            conversation_id = event_data.get('conversation', {}).get('id', '').replace(':', '_')
            message_id = event_data.get('id')
            session_name = f"{conversation_id}-{message_id}.txt"
        else:
            message_id = event_data.get('conversation', {}).get('id', '').replace(':', '_')
            session_name = f"{user_id}-{message_id}.txt"

        processing_container = self.backend_internal_data_processing_dispatcher.processing
        result = await self.backend_internal_data_processing_dispatcher.read_data_content(processing_container, session_name)

        if result is not None:
            self.logger.warning(f"Discarding request: This request is already being processed for {session_name}")
            return True
        return False

    async def send_message(self, message, event: IncomingNotificationDataBase, message_type=MessageType.TEXT, title=None, is_internal=False, show_ref=False):

        if (is_internal == False and show_ref == False):
            # Convert event_data to an Activity
            auth_header = self.headers["Authorization"] if "Authorization" in self.headers else ""
            self.activity.text = message
            response = await self.adapter.process_activity(self.activity, auth_header, self.BOT.on_turn)

    async def request_to_notification_data(self, event_data):
        activity = Activity().deserialize(event_data)
        timestamp = self._get_timestamp(activity)
        turn_context = await self._create_turn_context(activity)

        user_id, user_name, channel_id = self._extract_user_info(activity)
        text = activity.text
        is_mention = self._check_is_mention(activity)
        conversation_id, ts, thread_id, event_label = self._extract_conversation_info(event_data)

        base64_images = await self._process_image_attachments(activity)
        files_content = []

        event_type = event_data.get('type')

        if event_type == 'message':
            return self._create_teams_event_data(
                timestamp, ts, event_label, channel_id, thread_id, user_name, user_id,
                is_mention, text, base64_images, files_content, event_data
            )
        else:
            self.logger.info(f"Ignoring event type {event_type}")
            return None

    def _get_timestamp(self, activity):
        return activity.timestamp.timestamp() if activity.timestamp else datetime.now().timestamp()

    async def _create_turn_context(self, activity):
        connector_client = ConnectorClient(self.credentials, base_url=activity.service_url)
        turn_context = TurnContext(self.adapter, activity)
        turn_context.turn_state[self.adapter.BOT_CONNECTOR_CLIENT_KEY] = connector_client
        return turn_context

    def _extract_user_info(self, activity):
        user_id = activity.from_property.aad_object_id if activity.from_property else None
        user_name = activity.from_property.name if activity.from_property else None
        channel_id = activity.conversation.id if activity.conversation else None
        return user_id, user_name, channel_id

    def _check_is_mention(self, activity):
        return any(
            entity.type == 'mention' and
            entity.additional_properties.get('mentioned', {}).get('id') == self.bot_user_id
            for entity in (activity.entities or [])
        )

    def _extract_conversation_info(self, event_data):
        conversation_id = event_data.get('conversation', {}).get('id', '').replace(':', '_')
        ts = event_data.get('id')
        thread_id = conversation_id.split(';messageid=')[1].replace(':', '_') if ';messageid=' in conversation_id else ''
        event_label = "thread_message" if ts != thread_id else "message"
        return conversation_id, ts, thread_id, event_label

    async def _process_image_attachments(self, activity):
        base64_images = []
        if activity.attachments:
            for attachment in activity.attachments:
                if attachment.content_type.startswith("image/"):
                    base64_image = await self._process_single_image_attachment(attachment)
                    if base64_image:
                        base64_images.append(base64_image)
        return base64_images

    async def _process_single_image_attachment(self, attachment):
        if attachment.content_url:
            try:
                image_response = requests.get(attachment.content_url)
                image_response.raise_for_status()
                return base64.b64encode(image_response.content).decode('utf-8')
            except requests.RequestException as e:
                self.logger.error(f"Failed to fetch image: {e}")
        elif attachment.content and 'base64' in attachment.content:
            return attachment.content.split('base64,')[1]
        return None

    def _create_teams_event_data(self, timestamp, ts, event_label, channel_id, thread_id,
                                user_name, user_id, is_mention, text, base64_images,
                                files_content, event_data):
        return TeamsEventData(
            timestamp=ts,
            event_label=event_label,
            channel_id=channel_id,
            thread_id=thread_id,
            response_id=ts,
            user_name=user_name,
            user_email="",
            user_id=user_id,
            is_mention=is_mention,
            text=text,
            images=base64_images,
            files_content=files_content,
            #origin=inspect.currentframe().f_back.f_globals['__name__'],
            raw_data=event_data,
            origin_plugin_name=self.teams_config.PLUGIN_NAME
        )

    async def add_reaction(self, event, channel_id, timestamp, reaction_name):
        auth_header = self.headers.get("Authorization", "") if hasattr(self, 'headers') else ""
        if not hasattr(self, 'activity'):
            self.activity = Activity(type="message")
        self.activity.text = f"special action {reaction_name}"
        # Trigger the activity
        response = await self.adapter.process_activity(self.activity, auth_header, self.BOT.on_turn)

    async def format_trigger_genai_message(self, message):
        # NOT IMPLEMENTED YET
        pass

    async def upload_file(self, event, file_content, filename, title, is_internal= False):
        # NOT IMPLEMENTED YET
        pass

    async def remove_reaction(self, event, channel_id, timestamp, reaction_name):
        # NOT IMPLEMENTED YET
        pass

    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        # NOT IMPLEMENTED YET
        pass

    def get_bot_id(self) -> str:
        return self.teams_config.TEAMS_APP_ID

    async def remove_reaction_from_thread(self, channel_id: str, thread_id: str, reaction_name: str):
        # NOT IMPLEMENTED YET
        raise NotImplementedError("remove_reaction_from_thread is not implemented in Teams plugin.")
