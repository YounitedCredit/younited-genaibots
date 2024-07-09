from plugins import IncomingNotificationDataBase


class TeamsEventData(IncomingNotificationDataBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
