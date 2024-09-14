import asyncio
import json
from typing import List, Optional

import aiohttp
from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.outgoing_notification_data_base import (
    OutgoingNotificationDataBase,
)
from core.user_interactions.outgoing_notification_event_types import (
    OutgoingNotificationEventTypes,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from plugins.user_interactions.custom_api.generic_rest.utils.genereic_rest_reactions import (
    GenericRestReactions,
)
from utils.logging.logger_loader import logging
from utils.plugin_manager.plugin_manager import PluginManager


class RestConfig(BaseModel):
    PLUGIN_NAME: str
    GENERIC_REST_ROUTE_PATH: str
    GENERIC_REST_ROUTE_METHODS: List[str]
    GENERIC_REST_BEHAVIOR_PLUGIN_NAME: str
    GENERIC_REST_MESSAGE_URL: str
    GENERIC_REST_REACTION_URL: str

class GenericRestPlugin(UserInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager :GlobalManager = global_manager
        self.plugin_manager :PluginManager = global_manager.plugin_manager
        self.logger = global_manager.logger
        self._reactions = GenericRestReactions()
        self.plugin_configs = global_manager.config_manager.config_model.PLUGINS
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None
        config_dict = global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.CUSTOM_API["GENERIC_REST"]
        self.rest_config = RestConfig(**config_dict)

    def initialize(self):
        self._route_path = self.rest_config.GENERIC_REST_ROUTE_PATH
        self._route_methods = self.rest_config.GENERIC_REST_ROUTE_METHODS
        self.plugin_name = self.rest_config.PLUGIN_NAME

        # Dispatchers
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    @property
    def route_path(self):
        return self._route_path

    @property
    def route_methods(self):
        return self._route_methods

    @property
    def plugin_name(self):
        return "generic_rest"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def reactions(self):
        return self._reactions

    async def handle_request(self, request: Request):
        try:
            self.logger.debug(f"request received: {request}")
            raw_body = await request.body()
            raw_body_str = raw_body.decode('utf-8')
            event_data_dict = json.loads(raw_body_str)
            event_data = IncomingNotificationDataBase.from_dict(event_data_dict)
            event_data.origin_plugin_name = self.plugin_name
            headers = request.headers
            self.logger.info(f"Request received from <{request.url.path}>")

            # Create a new task to handle the rest of the processing
            asyncio.create_task(self.process_event_data(event_data, headers, raw_body_str))

            return Response("Request accepted for processing", status_code=202)

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received")
            return Response("Invalid JSON", status_code=400)
        except Exception as e:
            self.logger.exception(f"Error processing request from <{request.headers.get('Referer')}>: {e}")
            return Response("Internal server error", status_code=500)

    async def validate_request(self, event_data = None, headers = None, raw_body_str = None):
        try:
            # Convert JSON to dict
            data = json.loads(raw_body_str)

            # Get required keys from IncomingNotificationDataBase
            default_instance = IncomingNotificationDataBase.from_dict({})
            required_keys = default_instance.to_dict().keys()

            # Check if all required keys are in data
            if not all(key in data for key in required_keys):
                missing_keys = [key for key in required_keys if key not in data]
                self.logger.error(f"Missing keys in data received from {self.route_path}: {', '.join(missing_keys)}")
                self.logger.debug(f"Data received: {data}")
                return False

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON received")
            return False
        except Exception as e:
            self.logger.error(f"Error converting data to IncomingNotificationDataBase: {e}")
            return False

        self.logger.info("Request validated")
        return True

    async def process_event_data(self, event_data : IncomingNotificationDataBase, headers, raw_body_str):
        try:
            validate_request = await self.validate_request(event_data, headers, raw_body_str)

            if validate_request == True:
                try:
                    user_id = event_data.user_id
                    channel_id = event_data.channel_id
                    self.logger.info(f"Valid <GENERIC_REST> request received from user {user_id} in channel {channel_id}, processing..")
                    await self.global_manager.user_interactions_behavior_dispatcher.process_interaction(
                        event_data=event_data,
                        event_origin= self.plugin_name,
                        plugin_name=self.rest_config.GENERIC_REST_BEHAVIOR_PLUGIN_NAME
                    )

                except Exception as e:
                    logging.error(f"An error occurred while processing user input: {e}")
                    raise
            else:
                self.logger.info("Request discarded")
        except Exception as e:
            self.logger.exception(f"An error occurred while processing user input: {e}")
            raise  # re-raise the exception

    async def send_message(self, message, event, message_type=MessageType.TEXT, title=None, is_internal=False, show_ref=False):
        notification : OutgoingNotificationDataBase = OutgoingNotificationDataBase.from_incoming_notification_data(incoming_notification_data=event,event_type= OutgoingNotificationEventTypes.MESSAGE)
        notification.text = message
        notification.message_type = message_type
        await self.post_notification(notification, self.rest_config.GENERIC_REST_MESSAGE_URL)

    async def upload_file(self, event, file_content, filename, title, is_internal=False):
        raise NotImplementedError

    async def add_reaction(self, event : IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        notification : OutgoingNotificationDataBase = OutgoingNotificationDataBase.from_incoming_notification_data(incoming_notification_data=event,event_type= OutgoingNotificationEventTypes.REACTION_ADD)
        notification.event_type = OutgoingNotificationEventTypes.REACTION_ADD
        notification.reaction_name = reaction_name
        await self.post_notification(notification, self.rest_config.GENERIC_REST_REACTION_URL)

    async def remove_reaction(self, event, channel_id, timestamp, reaction_name):
        notification : OutgoingNotificationDataBase = OutgoingNotificationDataBase.from_incoming_notification_data(incoming_notification_data=event,event_type= OutgoingNotificationEventTypes.REACTION_REMOVE)
        notification.event_type = OutgoingNotificationEventTypes.REACTION_REMOVE
        notification.reaction_name = reaction_name
        await self.post_notification(notification, self.rest_config.GENERIC_REST_REACTION_URL)

    async def request_to_notification_data(self, event_data):
        notification_data : IncomingNotificationDataBase = IncomingNotificationDataBase.from_dict(event_data)
        return notification_data

    def format_trigger_genai_message(self, message):
        raise NotImplementedError

    async def post_notification(self, notification: OutgoingNotificationDataBase, url):
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(notification.to_dict())
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to post notification: {await response.text()}")
                else:
                    self.logger.info("Notification posted successfully.")

    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        # NOT IMPLEMENTED YET
        pass
