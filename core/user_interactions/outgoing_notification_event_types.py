from enum import Enum


class OutgoingNotificationEventTypes(Enum):
    MESSAGE = "message"
    REACTION_ADD = "reaction_add"
    REACTION_REMOVE = "reaction_remove"
    FILE_UPLOAD = "file_upload"
    AUDIO_UPLOAD = "audio_upload"
