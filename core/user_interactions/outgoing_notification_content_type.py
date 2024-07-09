from enum import Enum


class OutgoingNotificationContentType(Enum):
    TEXT = "text"
    COMMENT = "comment"
    CODEBLOCK = "codeblock"
    CUSTOMCONTENT = "customcontent"
