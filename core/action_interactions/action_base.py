from abc import ABC, abstractmethod

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class ActionBase(ABC):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        super().__init__()
        self.global_manager: GlobalManager = global_manager

    @abstractmethod
    def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        pass
