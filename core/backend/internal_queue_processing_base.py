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
    def messages_queue_ttl(self):
        """
        Property for the messages queue TTL.
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
    def internal_events_queue_ttl(self):
        """
        Property for the internal events queue TTL.
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
    def external_events_queue_ttl(self):
        """
        Property for the external events queue TTL.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def wait_queue(self):
        """
        Property for the wait queue container.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def wait_queue_ttl(self):
        """
        Property for the wait queue TTL.
        """
        raise NotImplementedError

    @abstractmethod
    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, message: str,
                              guid: str) -> None:
        """
        Adds a message to the queue for a given channel, thread, and message_id, using a GUID for uniqueness.
        """
        raise NotImplementedError

    @abstractmethod
    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str,
                              guid: str) -> None:
        """
        Removes a message from the queue based on channel_id, thread_id, message_id, and guid.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str) -> Tuple[
        Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message from the queue for the given channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str,
                                 current_message_id: str) -> bool:
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

    @abstractmethod
    async def cleanup_expired_messages(self, data_container: str, channel_id: str, thread_id: str,
                                       ttl_seconds: int) -> None:
        """
        Cleans up expired messages for a given thread/channel in the queue based on TTL.
        Removes messages whose creation time exceeds the TTL.
        """
        raise NotImplementedError

    @abstractmethod
    async def clean_all_queues(self) -> None:
        """
        Cleans up expired messages across all queues at startup based on TTL.
        This ensures no expired messages remain in the system across all channels and threads.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear_all_queues(self) -> None:
        """
        Clears all messages across all queues, regardless of TTL.
        This removes all messages in the system across all channels and threads.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_container(self, data_container: str) -> None:
        """
        Creates a new container for storing messages.
        """
        raise NotImplementedError
