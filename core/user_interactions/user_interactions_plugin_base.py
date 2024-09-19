from abc import ABC, abstractmethod
from typing import List, Optional

from core.plugin_base import PluginBase
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.reaction_base import ReactionBase


class UserInteractionsPluginBase(PluginBase, ABC):
    """
    Abstract base class for user interactions plugins.
    """

    @property
    @abstractmethod
    def route_path(self):
        """
        Property for the route path.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def route_methods(self):
        """
        Property for the route methods.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def reactions(self) -> ReactionBase:
        """
        Property for the reactions.
        """
        raise NotImplementedError

    @reactions.setter
    @abstractmethod
    def reactions(self, value: ReactionBase):
        """
        Setter for the reactions.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_request(self, request):
        """
        Determines whether the plugin can handle the given request.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_request(self, request):
        """
        Handles the request.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message, event: IncomingNotificationDataBase, message_type=MessageType.TEXT, title=None, is_internal=False, show_ref=False):
        """
        Asynchronously send a message to a specified channel.
        """
        raise NotImplementedError

    @abstractmethod
    async def upload_file(self, event :IncomingNotificationDataBase, file_content, filename, title, is_internal=False):
        """
        Asynchronously upload a file to a specified channel.
        """
        raise NotImplementedError

    @abstractmethod
    async def add_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        """
        Add a reaction to a message in a specified channel.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        """
        Remove a reaction from a message in a specified channel.
        """
        raise NotImplementedError

    @abstractmethod
    def request_to_notification_data(self, event_data):
        """
        Convert a request to notification data.
        """
        raise NotImplementedError

    @abstractmethod
    def format_trigger_genai_message(self, message):
        """
        Format a trigger user message.

        Args:
            message (_type_): _description_

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    @abstractmethod
    async def process_event_data(self, event_data, headers, request_json):
        """
        Process event data.

        Args:
            event_data (_type_): _description_
            headers (_type_): _description_
            request_json (_type_): _description_

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        """
        Fetches the conversation history for a given channel and thread.
        Plugins must implement this method. If channel_id and thread_id are provided,
        they will be used instead of the event data.
        """
        raise NotImplementedError

    @abstractmethod
    def get_bot_id(self) -> str:
        """
        Get the bot ID.

        Returns:
            str: The bot ID.
        """
        raise NotImplementedError