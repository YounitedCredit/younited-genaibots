from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType

from .outgoing_notification_event_types import OutgoingNotificationEventTypes


class OutgoingNotificationDataBase:
    """
    A class to represent outgoing notification data.

    Attributes
    ----------
    channel_id : str
        The ID of the channel where the event occurred.
    event_type : str
        The label of the event that triggered the notification.
    files_content : list, optional
        A list of file contents that were sent as part of the event (default is []).
    images : list, optional
        A list of images that were sent as part of the event (default is []).
    is_mention : bool
        A flag indicating whether the user was mentioned in the event.
    message_type: : message_type
        Determine the message type for the notification
    origin : str
        The original source of the user interaction that triggered the event.
    origin_plugin_name : str, optional
        The name of the plugin that originated the event (default is None).
    raw_data : dict, optional
        The raw data of the event (default is None).
    reaction_name : str, optional
        The name of the reaction that was triggered (default is None).
    response_id : str
        The timestamp when the response to the event was created.
    text : str
        The text of the message that was sent as part of the event.
    thread_id : str
        The timestamp of the thread where the event occurred.
    timestamp : str
        The timestamp when the notification was created.
    user_email : str
        The email of the user who triggered the event.
    user_id : str
        The ID of the user who triggered the event.
    user_name : str
        The name of the user who triggered the event.

    Methods
    -------
    to_dict():
        Returns the attributes of the object as a dictionary.
    """

    def __init__(self, channel_id, event_type : OutgoingNotificationEventTypes, is_mention, origin, response_id, thread_id, timestamp, user_email, user_id, user_name, files_content=None, images=None, origin_plugin_name=None, raw_data=None, reaction_name=None, message_type : MessageType = None, text = None):
        self.channel_id = channel_id
        self.event_type = event_type
        self.files_content = files_content if files_content is not None else []
        self.images = images if images is not None else []
        self.is_mention = is_mention
        self.message_type = message_type
        self.origin = origin
        self.origin_plugin_name = origin_plugin_name
        self.raw_data = raw_data
        self.reaction_name = reaction_name
        self.response_id = response_id
        self.text = text
        self.thread_id = thread_id
        self.timestamp = timestamp
        self.user_email = user_email
        self.user_id = user_id
        self.user_name = user_name

    def to_dict(self):
        return {
            'channel_id': self.channel_id,
            'event_type': self.event_type.name if self.event_type else None,
            'files_content': self.files_content,
            'images': self.images,
            'is_mention': self.is_mention,
            'message_type': self.message_type.name if self.message_type else None,  # Check if message_type is not None
            'origin': self.origin,
            'origin_plugin_name': self.origin_plugin_name,
            'raw_data': self.raw_data,
            'reaction_name': self.reaction_name,
            'response_id': self.response_id,
            'text': self.text,
            'thread_id': self.thread_id,
            'timestamp': self.timestamp,
            'user_email': self.user_email,
            'user_id': self.user_id,
            'user_name': self.user_name
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            channel_id=data.get('channel_id'),
            event_type=data.get('event_type'),
            files_content=data.get('files_content'),
            images=data.get('images'),
            is_mention=data.get('is_mention'),
            message_type= data.get('message_type'),
            origin=data.get('origin'),
            origin_plugin_name=data.get('origin_plugin_name'),
            raw_data=data.get('raw_data'),
            reaction_name=data.get('reaction_name'),
            response_id=data.get('response_id'),
            text=data.get('text'),
            thread_id=data.get('thread_id'),
            timestamp=data.get('timestamp'),
            user_email=data.get('user_email'),
            user_id=data.get('user_id'),
            user_name=data.get('user_name')
        )

    @classmethod
    def from_incoming_notification_data(cls, incoming_notification_data: IncomingNotificationDataBase, event_type: OutgoingNotificationEventTypes):
        return cls(
            channel_id=incoming_notification_data.channel_id,
            event_type = event_type,
            is_mention=incoming_notification_data.is_mention,
            origin=incoming_notification_data.origin,
            origin_plugin_name=incoming_notification_data.origin_plugin_name,
            raw_data=incoming_notification_data.raw_data,
            response_id=incoming_notification_data.response_id,
            thread_id=incoming_notification_data.thread_id,
            timestamp=incoming_notification_data.timestamp,
            user_email=incoming_notification_data.user_email,
            user_id=incoming_notification_data.user_id,
            user_name=incoming_notification_data.user_name
        )
