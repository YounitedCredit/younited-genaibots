from typing import List, Dict, Optional

class IncomingNotificationDataBase:
    """
    A class to represent incoming notification data with strong typing.

    Attributes
    ----------
    timestamp : str
        The timestamp when the notification was created (in universal time format like Slack's .ts).
    event_label : str
        The label of the event that triggered the notification.
    channel_id : str
        The ID of the channel where the event occurred.
    thread_id : str
        The ID of the thread where the event occurred.
    response_id : str
        The ID of the response to the event.
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
    images : List[str], optional
        A list of images that were sent as part of the event (default is []).
    files_content : List[str], optional
        A list of file contents that were sent as part of the event (default is []).
    raw_data : Optional[Dict], optional
        The raw data of the event (default is None).
    origin_plugin_name : str
        The name of the plugin that originated the event.

    Methods
    -------
    to_dict():
        Returns the attributes of the object as a dictionary.
    """

    def __init__(
        self,
        timestamp: str,
        event_label: str,
        channel_id: str,
        thread_id: str,
        response_id: str,
        is_mention: bool,
        text: str,
        origin: str,
        origin_plugin_name: str,
        app_id: Optional[str] = None,
        api_app_id: Optional[str] = None,
        username: Optional[str] = None,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        images: Optional[List[str]] = None,
        files_content: Optional[List[str]] = None,
        raw_data: Optional[Dict] = None
    ) -> None:
        self.timestamp: str = timestamp
        self.event_label: str = event_label
        self.channel_id: str = str(channel_id)  # Ensures channel_id is always a string
        self.thread_id: str = str(thread_id)  # Ensures thread_id is always a string
        self.response_id: str = str(response_id)  # Ensures response_id is always a string
        self.user_name: str = user_name if user_name is not None else ""
        self.user_email: str = user_email if user_email is not None else ""
        self.user_id: str = user_id if user_id is not None else ""
        self.app_id: str = app_id if app_id is not None else ""
        self.api_app_id: str = api_app_id if api_app_id is not None else ""
        self.username: str = username if username is not None else ""
        self.is_mention: bool = is_mention
        self.text: str = text
        self.origin: str = origin
        self.origin_plugin_name: str = origin_plugin_name  # Mandatory string field
        self.images: List[str] = images if images is not None else []
        self.files_content: List[str] = files_content if files_content is not None else []
        self.raw_data: Optional[Dict] = raw_data

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            'timestamp': self.timestamp,
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
            'origin_plugin_name': self.origin_plugin_name,
            'images': self.images,
            'files_content': self.files_content,
            'raw_data': self.raw_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Optional[str]]) -> 'IncomingNotificationDataBase':
        return cls(
            timestamp=data.get('timestamp', ''),
            event_label=data.get('event_label', ''),
            channel_id=str(data.get('channel_id', '')),
            thread_id=str(data.get('thread_id', '')),
            response_id=str(data.get('response_id', '')),
            app_id=data.get('app_id'),
            api_app_id=data.get('api_app_id'),
            username=data.get('username'),
            user_name=data.get('user_name'),
            user_email=data.get('user_email'),
            user_id=data.get('user_id'),
            is_mention=data.get('is_mention', False),
            text=data.get('text', ''),
            origin=data.get('origin', ''),
            origin_plugin_name=data.get('origin_plugin_name', ''),
            images=data.get('images', []),
            files_content=data.get('files_content', []),
            raw_data=data.get('raw_data')
        )
