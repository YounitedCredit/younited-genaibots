from abc import ABC, abstractmethod
from typing import Any

from core.plugin_base import PluginBase
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class UserInteractionsBehaviorBase(PluginBase, ABC):
    @abstractmethod
    async def process_interaction(self, event_data: Any, event_origin: Any) -> None:
        pass

    @abstractmethod
    async def process_incoming_notification_data(self, event: IncomingNotificationDataBase) -> None:
        pass

    @abstractmethod
    async def begin_genai_completion(self, event: IncomingNotificationDataBase, channel_id: str,
                                     timestamp: str) -> None:
        pass

    @abstractmethod
    async def end_genai_completion(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass

    @abstractmethod
    async def begin_long_action(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass

    @abstractmethod
    async def end_long_action(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass

    @abstractmethod
    async def begin_wait_backend(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass

    @abstractmethod
    async def end_wait_backend(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass

    @abstractmethod
    async def mark_error(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str) -> None:
        pass
