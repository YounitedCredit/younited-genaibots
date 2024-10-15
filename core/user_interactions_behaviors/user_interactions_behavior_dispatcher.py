import inspect
from typing import Any, List, Optional

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from core.user_interactions_behaviors.user_interactions_behavior_base import (
    UserInteractionsBehaviorBase,
)
from utils.config_manager.config_model import BotConfig


class UserInteractionsBehaviorsDispatcher(UserInteractionsBehaviorBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugins : List[UserInteractionsPluginBase] = []
        self.default_plugin_name = None
        self.default_plugin : Optional[UserInteractionsPluginBase] = None

    def initialize(self, plugins: List[UserInteractionsPluginBase] = None):

        self.bot_config : BotConfig = self.global_manager.bot_config

        if not plugins:
            self.logger.error("No plugins provided for UserInteractionsBehaviorsDispatcher")
            return

        self.plugins = plugins
        if self.bot_config.USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME is not None:
            self.logger.info(f"Setting default User Interactions behavior plugin to <{self.bot_config.USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME}>")
            self.default_plugin : UserInteractionsBehaviorBase= self.get_plugin(self.bot_config.USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME)
            self.default_plugin_name = self.default_plugin.plugin_name
        else:
            self.default_plugin = plugins[0]
            self.default_plugin_name = self.default_plugin.plugin_name
            self.logger.info(f"Setting User Interactions behavior default plugin to first plugin in list <{self.default_plugin_name}>")

    def get_plugin(self, plugin_name=None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        # Flatten the list of plugins
        all_plugins = [plugin for plugins_in_category in self.plugins.values() for plugin in plugins_in_category]

        # Iterate over the flattened list to find the plugin
        for plugin in all_plugins:
            if plugin.plugin_name == plugin_name:
                return plugin

        self.logger.error(f"UserInteractionsInstantMessagingDispatcher: Plugin '{plugin_name}' not found, returning default plugin")

        if self.default_plugin is None:
            self.logger.error("No default plugin set. Unable to proceed without a valid plugin.")
            raise RuntimeError("No default plugin set. Unable to proceed without a valid plugin.")

        return self.default_plugin
        def set_default_plugin(self, plugin_name):
            self.default_plugin_name = plugin_name
            self.default_plugin = self.get_plugin(plugin_name)

    @property
    def plugins(self) -> List[UserInteractionsPluginBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[UserInteractionsPluginBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin : UserInteractionsPluginBase = self.get_plugin()
        plugin.plugin_name = value

    async def process_interaction(self, event_data: Any, event_origin: Any, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(
                f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}"
            )
            return
        await plugin.process_interaction(event_data, event_origin)

    async def process_incoming_notification_data(self, event: IncomingNotificationDataBase, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.process_incoming_notification_data(event)

    async def begin_genai_completion(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.begin_genai_completion(event, channel_id=channel_id, timestamp=timestamp)

    async def end_genai_completion(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.end_genai_completion(event, channel_id, timestamp)

    async def begin_long_action(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.begin_long_action(event, channel_id, timestamp)

    async def end_long_action(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.end_long_action(event, channel_id, timestamp)

    async def begin_wait_backend(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.begin_wait_backend(event, channel_id, timestamp)

    async def end_wait_backend(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.end_wait_backend(event, channel_id, timestamp)

    async def mark_error(self, event: IncomingNotificationDataBase, channel_id: str, timestamp: str, plugin_name = None):
        plugin : UserInteractionsBehaviorBase = self.get_plugin(plugin_name)
        if plugin is None:
            current_method = inspect.currentframe().f_code.co_name
            self.logger.error(f"Error calling {current_method} in UserInteractionsBehaviorDispatcher: Plugin not found: {plugin_name}")
            return
        await plugin.mark_error(event, channel_id, timestamp)

