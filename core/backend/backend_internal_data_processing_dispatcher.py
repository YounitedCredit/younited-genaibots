from typing import List, Optional, Tuple

from core.backend.internal_data_processing_base import InternalDataProcessingBase


class BackendInternalDataProcessingDispatcher(InternalDataProcessingBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugins : List[InternalDataProcessingBase] = []
        self.default_plugin_name = None
        self.default_plugin: Optional[InternalDataProcessingBase] = None

    def initialize(self, plugins: List[InternalDataProcessingBase] = None):
        if not plugins:
            self.logger.error("No plugins provided for BackendInternalDataProcessingDispatcher")
            return

        self.plugins = plugins
        self.default_plugin_name = self.global_manager.bot_config.INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME
        self.default_plugin = self.get_plugin(self.default_plugin_name)

    def get_plugin(self, plugin_name = None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        for plugin in self.plugins:
            if plugin.plugin_name == plugin_name:
                return plugin

        self.logger.error(f"BackendInternalDataProcessingDispatcher: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin

    @property
    def plugins(self) -> List[InternalDataProcessingBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[InternalDataProcessingBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin : InternalDataProcessingBase = self.get_plugin()
        plugin.plugin_name = value

    @property
    def sessions(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.sessions

    @property
    def feedbacks(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.feedbacks

    @property
    def concatenate(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.concatenate

    @property
    def prompts(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.prompts

    @property
    def costs(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.costs

    @property
    def processing(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.processing

    @property
    def abort(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.abort

    @property
    def vectors(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.vectors

    @property
    def subprompts(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.subprompts

    @property
    def custom_actions(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.custom_actions

    @property
    def messages_queue(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.messages_queue

    def append_data(self, container_name: str, data_identifier: str, data: str = None):
        plugin: InternalDataProcessingBase = self.get_plugin(container_name)
        plugin.append_data(container_name, data_identifier, data)

    async def read_data_content(self, data_container, data_file, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.read_data_content(data_container= data_container, data_file= data_file)

    async def write_data_content(self, data_container, data_file, data, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.write_data_content(data_container= data_container, data_file= data_file, data= data)

    async def update_pricing(self, container_name, datafile_name, pricing_data, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.update_pricing(container_name= container_name, datafile_name= datafile_name, pricing_data= pricing_data)

    async def update_prompt_system_message(self, channel_id, thread_id, message, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.update_prompt_system_message(channel_id= channel_id, thread_id= thread_id, message= message)

    async def update_session(self, data_container, data_file, role, content, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.update_session(data_container= data_container, data_file= data_file, role= role, content= content)

    async def remove_data_content(self, data_container, data_file, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.remove_data_content(data_container= data_container, data_file= data_file)

    async def list_container_files(self, container_name, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.list_container_files(container_name= container_name)

    async def enqueue_message(self, channel_id: str, thread_id: str, message_id :str, message: str, plugin_name: Optional[str] = None) -> None:
        """
        Adds a message to the queue for a given channel and thread.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Enqueuing message in {channel_id}_{thread_id} through {plugin.plugin_name}.")
        await plugin.enqueue_message(channel_id=channel_id, thread_id=thread_id, message_id=message_id, message=message)

    async def dequeue_message(self, channel_id: str, thread_id: str, message_id: str, plugin_name: Optional[str] = None) -> None:
        """
        Removes a message from the queue after processing.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Dequeuing message {message_id} from {channel_id}_{thread_id} through {plugin.plugin_name}.")
        await plugin.dequeue_message(channel_id=channel_id, thread_id=thread_id, message_id=message_id)

    async def get_next_message(self, channel_id: str, thread_id: str, current_message_id: str, plugin_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message for a `channel_id` and `thread_id` after `current_message_id`.
        Returns a tuple (message_id, message_content). If no message is found, returns (None, None).
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Getting next message for channel '{channel_id}', thread '{thread_id}' with current message_id '{current_message_id}' through {plugin.plugin_name}.")
        return await plugin.get_next_message(channel_id=channel_id, thread_id=thread_id, current_message_id=current_message_id)

    async def has_older_messages(self, channel_id: str, thread_id: str, plugin_name: Optional[str] = None) -> bool:
        """
        Checks if there are any older messages waiting in the queue for the given channel and thread.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Checking for older messages in {channel_id}_{thread_id} through {plugin.plugin_name}.")
        return await plugin.has_older_messages(channel_id=channel_id, thread_id=thread_id)

    async def clear_messages_queue(self, channel_id: str, thread_id: str, plugin_name: Optional[str] = None) -> None:
        """
        Clears all messages in the queue for a given channel and thread.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Clearing messages queue for channel '{channel_id}', thread '{thread_id}' through {plugin.plugin_name}.")
        await plugin.clear_messages_queue(channel_id=channel_id, thread_id=thread_id)

    async def get_all_messages(self, channel_id: str, thread_id: str, plugin_name: Optional[str] = None) -> List[str]:
        """
        Retrieves the contents of all messages for a `channel_id` and `thread_id`.
        Returns a list of message contents.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Retrieving all messages for channel '{channel_id}', thread '{thread_id}' through {plugin.plugin_name}.")
        return await plugin.get_all_messages(channel_id=channel_id, thread_id=thread_id)

    def get_plugin(self, plugin_name = None):
        if plugin_name is None:
            return self.default_plugin

        for plugin in self.plugins:
            if plugin.plugin_name == plugin_name:
                return plugin

        self.logger.error(f"BackendInternalDataProcessingDispatcher: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin
