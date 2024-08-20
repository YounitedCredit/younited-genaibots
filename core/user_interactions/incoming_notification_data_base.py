class IncomingNotificationDataBase:
    """
    A class to represent incoming notification data.

    Attributes
    ----------
    timestamp : str
        The timestamp when the notification was created.
    converted_timestamp : str
        The timestamp converted to a specific format.
    event_label : str
        The label of the event that triggered the notification.
    channel_id : str
        The ID of the channel where the event occurred.
    thread_id : str
        The timestamp of the thread where the event occurred.
    response_id : str
        The timestamp when the response to the event was created.
    user_name : str
        The name of the user who triggered the event.
    user_email : str
        The email of the user who triggered the event.
    user_id : str
        The ID of the user who triggered the event.
    is_mention : bool
        A flag indicating whether the user was mentioned in the event.
    text : str
        The text of the message that was sent as part of the event.
    origin : str
        The original source of the user interaction that triggered the event.
    images : list, optional
        A list of images that were sent as part of the event (default is []).
    files_content : list, optional
        A list of file contents that were sent as part of the event (default is []).
    raw_data : dict, optional
        The raw data of the event (default is None).
    origin_plugin_name : str, optional
        The name of the plugin that originated the event (default is None).

    Methods
    -------
    to_dict():
        Returns the attributes of the object as a dictionary.
    """

    def __init__(self, timestamp, converted_timestamp, event_label, channel_id, thread_id, response_id, is_mention, text, origin, app_id=None, api_app_id=None, username=None, user_name=None, user_email=None, user_id=None, images=None, files_content=None, raw_data=None, origin_plugin_name=None):
        self.timestamp = timestamp
        self.converted_timestamp = converted_timestamp
        self.event_label = event_label
        self.channel_id = channel_id
        self.thread_id = thread_id
        self.response_id = response_id
        self.user_name = user_name if user_name is not None else ""
        self.user_email = user_email if user_email is not None else ""
        self.user_id = user_id if user_id is not None else ""
        self.app_id = app_id if app_id is not None else ""
        self.api_app_id = api_app_id if api_app_id is not None else ""
        self.username = username if username is not None else ""
        self.is_mention = is_mention
        self.text = text
        self.origin = origin
        self.images = images if images is not None else []
        self.files_content = files_content if files_content is not None else []
        self.raw_data = raw_data
        self.origin_plugin_name = origin_plugin_name

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'converted_timestamp': self.converted_timestamp,
            'event_label': self.event_label,
            'channel_id': self.channel_id,
            'thread_id': self.thread_id,
            'response_id': self.response_id,
            'user_name': self.user_name,
            'username': self.username,
            'user_email': self.user_email,
            'user_id': self.user_id,
            'app_id': self.app_id,
            'api_app_id': self.api_app_id,
            'is_mention': self.is_mention,
            'text': self.text,
            'origin': self.origin,
            'images': self.images,
            'files_content': self.files_content,
            'raw_data': self.raw_data,
            'origin_plugin_name': self.origin_plugin_name
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            timestamp=data.get('timestamp'),
            converted_timestamp=data.get('converted_timestamp'),
            event_label=data.get('event_label'),
            channel_id=data.get('channel_id'),
            thread_id=data.get('thread_id'),
            response_id=data.get('response_id'),
            app_id=data.get('app_id'),
            api_app_id=data.get('api_app_id'),
            username=data.get('username'),
            user_name=data.get('user_name'),
            user_email=data.get('user_email'),
            user_id=data.get('user_id'),
            is_mention=data.get('is_mention'),
            text=data.get('text'),
            origin=data.get('origin'),
            images=data.get('images'),
            files_content=data.get('files_content'),
            raw_data=data.get('raw_data'),
            origin_plugin_name=data.get('origin_plugin_name')
        )
