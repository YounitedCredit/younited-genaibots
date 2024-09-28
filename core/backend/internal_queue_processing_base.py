from abc import abstractmethod
from typing import List, Optional, Tuple

from core.backend.internal_data_plugin_base import InternalDataPluginBase


class InternalQueueProcessingBase(InternalDataPluginBase):
    """
    Abstract base class for queue-specific processing plugins.
    """

    @property
    @abstractmethod
    def messages_queue(self):
        """
        Property for the messages queue container.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def internal_events_queue(self):
        """
        Property for the internal events queue container.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def external_events_queue(self):
        """
        Property for the external events queue container.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def wait_queue(self):
        """
        Property for the wait queue container.
        """
        raise NotImplementedError

    @abstractmethod
    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message: str) -> None:
        """
        Adds a message to the queue for a given channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str) -> None:
        """
        Removes a message from the queue after processing.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message from the queue for the given channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are any older messages waiting in the queue for a given channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear_messages_queue(self, data_container: str, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_messages(self, data_container: str, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves the contents of all messages for a `channel_id` and `thread_id`.
        Returns a list of message contents.
        """
        raise NotImplementedError
