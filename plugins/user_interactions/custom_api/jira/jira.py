import asyncio
import json
from typing import List, Optional

import aiohttp
from aiohttp import web

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.reaction_base import ReactionBase
from core.user_interactions.user_interactions_plugin_base import UserInteractionsPluginBase

class JiraUserInteractionsPlugin(UserInteractionsPluginBase):
    """
    Jira plugin for user interactions.
    """

    def __init__(self, jira_base_url, jira_username, jira_api_token):
        self.jira_base_url = jira_base_url
        self.jira_username = jira_username
        self.jira_api_token = jira_api_token
        self._reactions = None  # Implement a ReactionBase instance if needed

    @property
    def route_path(self):
        return "/jira/webhook"

    @property
    def route_methods(self):
        return ["POST"]

    @property
    def reactions(self) -> ReactionBase:
        return self._reactions

    @reactions.setter
    def reactions(self, value: ReactionBase):
        self._reactions = value

    def validate_request(self, request):
        # Implement validation logic if necessary
        return True

    async def handle_request(self, request):
        event_data = await request.json()
        headers = request.headers
        await self.process_event_data(event_data, headers, event_data)
        return web.Response(status=200)

    async def send_message(
        self,
        message,
        event: IncomingNotificationDataBase,
        message_type=MessageType.TEXT,
        title=None,
        is_internal=False,
        show_ref=False,
    ):
        issue_key = event.channel_id  # Assuming channel_id is the issue key
        comment_body = message

        if title:
            comment_body = f"{title}\n\n{comment_body}"

        data = {
            "body": comment_body,
            "properties": {},
        }

        if is_internal:
            data["properties"]["sd.public.comment"] = {"internal": True}

        url = f"{self.jira_base_url}/rest/api/2/issue/{issue_key}/comment"

        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(self.jira_username, self.jira_api_token)) as session:
            async with session.post(url, json=data) as resp:
                if resp.status != 201:
                    raise Exception(f"Failed to send message to Jira: {resp.status}")

    async def upload_file(
        self,
        event: IncomingNotificationDataBase,
        file_content,
        filename,
        title,
        is_internal=False,
    ):
        issue_key = event.channel_id
        url = f"{self.jira_base_url}/rest/api/2/issue/{issue_key}/attachments"

        headers = {
            "X-Atlassian-Token": "no-check",
        }

        data = aiohttp.FormData()
        data.add_field("file", file_content, filename=filename, content_type="application/octet-stream")

        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(self.jira_username, self.jira_api_token)) as session:
            async with session.post(url, data=data, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to upload file to Jira: {resp.status}")

            # Optionally, add a comment referencing the attachment
            attachment_info = await resp.json()
            attachment_id = attachment_info[0]["id"]
            attachment_url = attachment_info[0]["content"]

            await self.send_message(
                f"{title}\n\nAttached file: [{filename}]({attachment_url})",
                event,
                is_internal=is_internal,
            )

    async def add_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        # Jira does not support reactions like Slack or other chat platforms
        pass

    async def remove_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        # Jira does not support reactions like Slack or other chat platforms
        pass

    def request_to_notification_data(self, event_data):
        # Extract necessary information from the webhook payload
        return IncomingNotificationDataBase(
            user_id=event_data["user"]["accountId"],
            channel_id=event_data["issue"]["key"],
            message=event_data["comment"]["body"],
            timestamp=event_data["comment"]["created"],
        )

    def format_trigger_genai_message(self, message):
        # Format the message if necessary
        return message

    async def process_event_data(self, event_data, headers, request_json):
        # Process the incoming webhook event
        notification_data = self.request_to_notification_data(event_data)
        # Handle the notification_data as per your application's logic
        # For example, pass it to a message handler or queue
        pass

    async def fetch_conversation_history(
        self,
        event: IncomingNotificationDataBase,
        channel_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> List[IncomingNotificationDataBase]:
        issue_key = channel_id or event.channel_id
        url = f"{self.jira_base_url}/rest/api/2/issue/{issue_key}/comment"

        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth(self.jira_username, self.jira_api_token)) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to fetch comments from Jira: {resp.status}")
                comments_data = await resp.json()

        conversation_history = []
        for comment in comments_data.get("comments", []):
            conversation_history.append(
                IncomingNotificationDataBase(
                    user_id=comment["author"]["accountId"],
                    channel_id=issue_key,
                    message=comment["body"],
                    timestamp=comment["created"],
                )
            )

        return conversation_history

    async def remove_reaction_from_thread(self, channel_id: str, thread_id: str, reaction_name: str):
        # Jira does not support reactions
        pass

    def get_bot_id(self) -> str:
        # Return the bot's user ID or account ID in Jira
        return self.jira_username
