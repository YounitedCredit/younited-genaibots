from plugins import IncomingNotificationDataBase


class SlackEventData(IncomingNotificationDataBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
