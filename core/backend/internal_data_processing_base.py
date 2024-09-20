from abc import abstractmethod
import time
from typing import Tuple, Optional
from core.backend.internal_data_plugin_base import InternalDataPluginBase
from typing import List

class InternalDataProcessingBase(InternalDataPluginBase):
    """
    Abstract base class for internal data processing plugins.
    """

    @property
    @abstractmethod
    def sessions(self):
        """
        Property for sessions data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def feedbacks(self):
        """
        Property for feedbacks data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def concatenate(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def prompts(self):
        """
        Property for prompts data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def costs(self):
        """
        Property for costs data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def abort(self):
        """
        Property for abort data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def abort(self):
        """
        Property for abort data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def processing(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def vectors(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def subprompts(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def custom_actions(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError
    
    @property
    @abstractmethod
    def messages_queue(self):
        """
        Property for concatenate data.
        """
        raise NotImplementedError


    @abstractmethod
    def append_data(self, container_name: str, data_identifier: str, data: str) -> None:
        """
        Append data to the data container.

        :param container_name: Name of the data container
        :param data_identifier: Identifier for the data
        :param data: The data to append
        """
        raise NotImplementedError

    @abstractmethod
    async def read_data_content(self, data_container, data_file):
        """
        Asynchronously read data content from a specified data container and file.

        :param data_container: The data container to read from
        :param data_file: The data file to read
        """
        raise NotImplementedError

    @abstractmethod
    async def write_data_content(self, data_container, data_file, data):
        """
        Asynchronously write data content to a specified data container and file.

        :param data_container: The data container to write to
        :param data_file: The data file to write
        :param data: The data to write
        """
        raise NotImplementedError
    
    @abstractmethod
    async def update_pricing(self, container_name, datafile_name, pricing_data):
        """
        Asynchronously update the pricing information for a specified container and blob.

        :param container_name: The name of the container
        :param blob_name: The name of the blob
        :param total_tokens: The total number of tokens
        :param prompt_tokens: The number of prompt tokens
        :param completion_tokens: The number of completion tokens
        :param total_cost: The total cost
        :param input_cost: The input cost
        :param output_cost: The output cost
        """
        raise NotImplementedError

    @abstractmethod
    async def update_prompt_system_message(self, channel_id, thread_id, message):
        """
        Asynchronously update the prompt system message for a specified channel and thread.

        :param channel_id: The ID of the channel
        :param thread_id: The timestamp of the thread
        :param message: The message to update
        """
        raise NotImplementedError

    @abstractmethod
    async def update_session(self, data_container, data_file, role, content):
        """
        Asynchronously update the session information for a specified data container and file.

        :param data_container: The data container
        :param data_file: The data file
        :param role: The role
        :param content: The content
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_data_content(self, data_container, data_file):
        """
        Asynchronously remove data content from a specified data container and file.

        :param data_container: The data container to remove from
        :param data_file: The data file to remove
        """
        raise NotImplementedError

    @abstractmethod
    async def list_container_files(self, container_name):
        """
        Asynchronously list the files in a specified container.

        :param container_name: The name of the container
        """
        raise NotImplementedError

    @abstractmethod
    async def enqueue_message(self, channel_id: str, thread_id: str, message: str) -> None:
        """
        Adds a message to the queue for a given channel and thread.

        :param channel_id: The ID of the channel.
        :param thread_id: The ID of the thread (often a timestamp).
        :param message: The message content to enqueue.
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    async def dequeue_message(self, channel_id: str, thread_id: str, message_id: str) -> None:
        """
        Removes a message from the queue after processing.

        :param channel_id: The ID of the channel.
        :param thread_id: The ID of the thread.
        :param message_id: The unique identifier of the message (e.g., channel_id_thread_id_message_id).
        :return: None
        """
        raise NotImplementedError

    @abstractmethod
    async def get_next_message(self, channel_id: str, thread_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message from the queue for the given channel and thread.

        :param channel_id: The ID of the channel.
        :param thread_id: The ID of the thread.
        :return: A tuple containing the message_id and the message content. If no messages exist, returns (None, None).
        """
        raise NotImplementedError

    @abstractmethod
    async def has_older_messages(self, channel_id: str, thread_id: str) -> bool:
        """
        Checks if there are any older messages waiting in the queue for a given channel and thread.

        :param channel_id: The ID of the channel.
        :param thread_id: The ID of the thread.
        :return: True if older messages exist in the queue, False otherwise.
        """
        raise NotImplementedError
    
    @abstractmethod
    async def clear_messages_queue(self, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel and thread.

        :param channel_id: The ID of the channel.
        :param thread_id: The ID of the thread.
        :return: None
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_all_messages(self, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves the contents of all messages for a `channel_id` and `thread_id`.
        Returns a list of message contents.
        """
        pass