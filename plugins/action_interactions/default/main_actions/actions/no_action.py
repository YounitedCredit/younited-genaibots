from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class NoAction(ActionBase):

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        # This method is intentionally left empty as a placeholder.
        # In some scenarios, no action is required, but the event handling structure
        # necessitates that this method be defined.
        pass
