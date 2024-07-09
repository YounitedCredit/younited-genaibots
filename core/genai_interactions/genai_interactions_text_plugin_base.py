from abc import ABC, abstractmethod

from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from plugins import IncomingNotificationDataBase


class GenAIInteractionsTextPluginBase(GenAIInteractionsPluginBase, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._genai_cost_base = None

    @property
    def genai_cost_base(self) -> GenAICostBase:
        if self._genai_cost_base is None:
            raise ValueError("GenAI cost base is not set")
        return self._genai_cost_base

    @genai_cost_base.setter
    def genai_cost_base(self, value: GenAICostBase):
        self._genai_cost_base = value

    @abstractmethod
    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase):
        pass

    @abstractmethod
    async def trigger_feedback(self, event: IncomingNotificationDataBase):
        """
        Handles a special interaction which is the trigger_feedback.
        This method updates the messages as the user with the result of an action.

        :param event: The incoming notification data
        :return: The result of triggering the feedback
        """
        raise NotImplementedError
