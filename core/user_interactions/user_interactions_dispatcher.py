from typing import List, Optional

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.reaction_base import ReactionBase
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from utils.config_manager.config_model import BotConfig


class UserInteractionsDispatcher(UserInteractionsPluginBase):
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
            self.logger.error("No plugins provided for UserInteractionsDispatcher")
            return

        self.plugins = plugins

    def get_plugin(self, plugin_name=None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        for plugins_in_category in self.plugins.values():
            for plugin in plugins_in_category:
                if plugin.plugin_name == plugin_name:
                    return plugin

        self.logger.error(f"UserInteractionsDispatcher: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin

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

    @property
    def route_path(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.route_path

    @property
    def route_methods(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.route_methods  # replace with your route methods

    @property
    def reactions(self, plugin_name = None) -> ReactionBase:
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.reactions  # replace with your reactions

    @reactions.setter
    def reactions(self, value: ReactionBase, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        plugin.reactions = value  # replace with your logic

    def validate_request(self, request, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.validate_request(request)

    def handle_request(self, request, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.handle_request(request)

    async def send_message(self, message, event: IncomingNotificationDataBase, message_type = MessageType.TEXT, title=None, is_internal=False, show_ref=False, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.send_message(message=message, event=event, message_type=message_type, title=title, is_internal=is_internal, show_ref=show_ref)

    async def upload_file(self, event :IncomingNotificationDataBase, file_content, filename, title, is_internal=False, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name

        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.upload_file(event=event, file_content=file_content, filename=filename, title=title, is_internal=is_internal)

    async def add_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name

        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=reaction_name)

    async def remove_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name

        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.remove_reaction(channel_id=channel_id, timestamp=timestamp, reaction_name=reaction_name)

    async def request_to_notification_data(self, event_data, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.request_to_notification_data(event_data)

    def format_trigger_genai_message(self, event: IncomingNotificationDataBase = None, message = None, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.format_trigger_genai_message(message)

    async def process_event_data(self, event: IncomingNotificationDataBase, headers, raw_body_str, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.process_event_data(event_data=event, headers=headers, raw_body_str=raw_body_str)

    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        """
        Fetch conversation history from the plugin for a given channel and thread.
        """
        plugin_name = event.origin_plugin_name
        plugin: UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.fetch_conversation_history(event=event, channel_id=channel_id, thread_id=thread_id)
