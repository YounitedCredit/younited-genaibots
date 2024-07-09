from abc import ABC, abstractmethod
from typing import Any

from core.action_interactions.action_input import ActionInput
from core.plugin_base import PluginBase
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class GenAIInteractionsPluginBase(PluginBase, ABC):
    @abstractmethod
    async def validate_request(self, event: IncomingNotificationDataBase) -> bool:
        """
        Determines whether the plugin can handle the given request.

        :param event: The incoming notification data
        :return: True if the plugin can handle the request, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def handle_request(self, event: IncomingNotificationDataBase) -> Any:
        """
        Handles the request.

        :param event: The incoming notification data
        :return: The result of handling the request
        """
        raise NotImplementedError

    @abstractmethod
    async def trigger_genai(self, event: IncomingNotificationDataBase) -> Any:
        """
        Updates the messages as the user with the result of an action.

        :param user_message: The user message
        :param event: The incoming notification data
        :return: The result of triggering the user
        """
        raise NotImplementedError

    @abstractmethod
    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase) -> Any:
        """
        Handles the action.

        :param action_input: The action input
        :return: The result of handling the action
        """
        raise NotImplementedError

