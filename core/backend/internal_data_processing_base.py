from abc import abstractmethod

from core.backend.internal_data_plugin_base import InternalDataPluginBase


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
    def messages(self):
        """
        Property for messages data.
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
    async def store_unmentioned_messages(self, channel_id, thread_id, message):
        """
        Store unmentioned messages from a specified channel and thread.

        :param channel_id: The ID of the channel
        :param thread_id: The timestamp of the thread
        :param message: The message to store
        """
        raise NotImplementedError

    @abstractmethod
    async def retrieve_unmentioned_messages(self, channel_id, thread_id):
        """
        Asynchronously retrieve unmentioned messages from a specified channel and thread.

        :param channel_id: The ID of the channel
        :param thread_id: The timestamp of the thread
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
