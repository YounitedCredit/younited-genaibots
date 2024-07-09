import json
import re
import traceback

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from utils.plugin_manager.plugin_manager import PluginManager


class SlackOutputHandler:
    def __init__(self, global_manager : GlobalManager, slack_config):
        from ..slack import SlackConfig
        self.slack_config : SlackConfig = slack_config
        self.global_manager : GlobalManager = global_manager
        self.logger = global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        # Create a WebClient instance
        self.slack_bot_token = slack_config.SLACK_BOT_TOKEN
        self.client = WebClient(token=self.slack_bot_token)

    # Function to add reaction to a message
    async def add_reaction(self, channel_id, timestamp, reaction):
        try:
            # Check if reaction name is valid
            if not re.match(r'^[\w-]+$', reaction):
                self.logger.error(f"Invalid reaction name: {reaction}")
                return

            self.client.reactions_add(
                channel=channel_id,
                timestamp=timestamp,
                name=reaction
            )
        except SlackApiError as e:
            if e.response["error"] == "already_reacted":
                self.logger.debug("Already reacted. Skipping.")
            elif e.response["error"] == "invalid_name":
                self.logger.error(f"Invalid reaction name: {reaction}")
            else:
                self.logger.exception(f"{e.response['error']} channel id {channel_id} timestamp {timestamp}")

    # Function to remove reaction from a message
    async def remove_reaction(self, channel_id, timestamp, reaction):
        try:
            self.client.reactions_remove(
                channel=channel_id,
                timestamp=timestamp,
                name=reaction
            )
        except SlackApiError as e:
            if e.response["error"] == "no_reaction":
                self.logger.debug("No reaction to remove. Skipping.")
            else:
                raise e  # Re-raise the exception if it's not 'no_reaction'

    async def send_slack_message(self, channel_id, response_id, message, message_type=MessageType.TEXT, title=None):
        headers = {'Authorization': f'Bearer {self.slack_bot_token}'}
        payload = {
            'channel': channel_id,
            'thread_ts': response_id  # Pour répondre dans un thread
        }

        if isinstance(message_type, str):
            try:
                message_type = MessageType(message_type)
            except ValueError:
                raise ValueError(f"{message_type} is not a valid MessageType")

        if message_type == MessageType.TEXT:
            blocks = [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }]
            payload['blocks'] = json.dumps(blocks)
        elif message_type.value in ["card", "codeblock", "comment", "file"]:
            # Pour 'card', 'codeblock', 'comment', et 'file', utilisez format_slack_message
            blocks = self.format_slack_message(title, message, message_format=message_type)
            payload['blocks'] = json.dumps(blocks)
        else:
            raise ValueError(f"Invalid message type: {message_type}. Use 'TEXT', 'CARD', 'CODEBLOCK', 'COMMENT', or 'FILE'.")

        response = requests.post('https://slack.com/api/chat.postMessage', headers=headers, json=payload)
        return response

    def format_slack_message(self, title, message_text, message_format: MessageType):
        if message_format.value == "text":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                }
            ]
        elif message_format.value == "card":
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_text
                    }
                },
                {
                    "type": "divider"
                }
            ]
        elif message_format.value == "codeblock":
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{message_text}```"
                    }
                }
            ]
        elif message_format.value == "comment":
            code_comment = f"`{message_text}`"
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": code_comment
                    }
                }
            ]
        elif message_format.value == "file":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"File: {message_text}"
                    }
                }
            ]
        else:
            raise ValueError(f"Unsupported message format: {message_format}")

        return blocks

    async def upload_file_to_slack(self, event :IncomingNotificationDataBase, file_content, filename, title):
        channel_id = event.channel_id
        thread_id = event.thread_id

        await self.send_slack_message(channel_id, thread_id, f"uploading file {filename} and processing it...", MessageType.COMMENT )

        if file_content == None or file_content == '':
            file_content = "Empty result"

        try:
            response = self.client.files_upload_v2(channel=channel_id, thread_ts=thread_id, title=title, filename=filename, content=file_content )
            return response
        except SlackApiError as e:
            # Handle exceptions
            error_traceback = traceback.format_exc()
            error_message = f":interrobang: Error uploading file: {str(error_traceback)}"
            self.logger.exception(f"An error occurred: :interrobang: Error upload file: {e.response.get('error', 'No error message available')}")
            await self.send_slack_message(channel_id, thread_id, error_message)
