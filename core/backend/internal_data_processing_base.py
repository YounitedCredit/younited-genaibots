from abc import abstractmethod

from core.backend.internal_data_plugin_base import InternalDataPluginBase


class InternalDataProcessingBase(InternalDataPluginBase):
    """
    Abstract base class for internal data processing plugins, excluding queue operations.
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
    def processing(self):
        """
        Property for processing data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def vectors(self):
        """
        Property for vectors data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def subprompts(self):
        """
        Property for subprompts data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def custom_actions(self):
        """
        Property for custom actions data.
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
        """
        raise NotImplementedError

    @abstractmethod
    async def write_data_content(self, data_container, data_file, data):
        """
        Asynchronously write data content to a specified data container and file.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_pricing(self, container_name, datafile_name, pricing_data):
        """
        Asynchronously update the pricing information for a specified container and file.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_prompt_system_message(self, channel_id, thread_id, message):
        """
        Asynchronously update the prompt system message for a specified channel and thread.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_session(self, data_container, data_file, role, content):
        """
        Asynchronously update the session information for a specified data container and file.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_data_content(self, data_container, data_file):
        """
        Asynchronously remove data content from a specified data container and file.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_container_files(self, container_name):
        """
        Asynchronously list the files in a specified container.
        """
        raise NotImplementedError
