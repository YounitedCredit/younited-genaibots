from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)



class SlackEventData(IncomingNotificationDataBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
