from typing import List, Optional

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from utils.config_manager.config_model import BotConfig


class GenaiVectorsearch(GenAIInteractionsPluginBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugins: List[GenAIInteractionsPluginBase] = []
        self.default_plugin_name = None
        self.default_plugin: Optional[GenAIInteractionsPluginBase] = None

    def initialize(self, plugins: List[GenAIInteractionsPluginBase] = None):
        self.bot_config: BotConfig = self.global_manager.bot_config

        if not plugins:
            self.logger.error("No plugins provided for GenaiVectorsearch")
            return

        self.plugins = plugins

        if self.bot_config.GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME is not None:
            self.logger.info(
                f"Setting default Genai Vector Search plugin to <{self.bot_config.GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME}>")
            self.default_plugin = self.get_plugin(
                self.bot_config.GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME)
        else:
            self.default_plugin = plugins[0]
            self.logger.info(
                "Setting Genai Vector Search default plugin to first plugin in list")

        self.default_plugin_name = self.default_plugin.plugin_name if self.default_plugin else None
        
        if self.default_plugin_name:
            self.logger.info(f"Default plugin set to: <{self.default_plugin_name}>")
        else:
            self.logger.warning("No default plugin could be set")

    def get_plugin(self, plugin_name=None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        for plugin in self.plugins:
            if plugin.plugin_name == plugin_name:
                return plugin

        self.logger.error(f"GenaiVectorsearch: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin

    @property
    def plugins(self) -> List[GenAIInteractionsPluginBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[GenAIInteractionsPluginBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name=None):
        plugin: GenAIInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin: GenAIInteractionsPluginBase = self.get_plugin()
        plugin.plugin_name = value

    def validate_request(self, event: IncomingNotificationDataBase, plugin_name=None):
        plugin: GenAIInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.validate_request(event)

    def handle_request(self, event: IncomingNotificationDataBase, plugin_name=None):
        plugin: GenAIInteractionsPluginBase = self.get_plugin(plugin_name)
        plugin.handle_request(event)

    async def trigger_genai(self, event: IncomingNotificationDataBase, plugin_name=None):
        plugin: GenAIInteractionsPluginBase = self.get_plugin(plugin_name)
        plugin.trigger_genai(event=event)

    async def handle_action(self, action_input: ActionInput, plugin_name=None):
        plugin: GenAIInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.handle_action(action_input)
