from enum import Enum


class MessageType(Enum):
    """
        An enumeration representing the different types of messages.

        Attributes
        ----------
        CARD : str
            A message of type card.
        CODEBLOCK : str
            A message of type code block.
        COMMENT : str
            A message of type comment.
        CUSTOM : str
            A message of type custom.
        ACCORDION : str
            A message of type accordion.

        Methods
        -------
        has_value(value: str) -> bool:
            Checks if the given value is a valid message type.
    """

    TEXT = "text"
    CODEBLOCK = "codeblock"
    COMMENT = "comment"
    FILE = "file"
    CUSTOM = "custom"
    PRIVATE = "private"

    @classmethod
    def has_value(cls, value):
        """
        Checks if the given value is a valid message type.

        Parameters
        ----------
        value : str
            The value to check.

        Returns
        -------
        bool
            True if the value is a valid message type, False otherwise.
        """
        return value in cls._value2member_map_
