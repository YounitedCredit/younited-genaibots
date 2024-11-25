from typing import TYPE_CHECKING, Dict, List, Optional

from core.backend.enriched_session import EnrichedSession
from core.backend.session_manager_plugin_base import SessionManagerPluginBase
from utils.config_manager.config_model import BotConfig

if TYPE_CHECKING:
    from core.global_manager import (
        GlobalManager,  # Forward reference to avoid circular import
    )

class SessionManagerDispatcher(SessionManagerPluginBase):
    def __init__(self, global_manager: 'GlobalManager'):
        self.global_manager = global_manager
        self.backend_dispatcher = None
        self.logger = global_manager.logger

    def initialize(self, plugins: List[SessionManagerPluginBase] = None):
        self.bot_config: BotConfig = self.global_manager.bot_config

        if not plugins:
            self.logger.error("No plugins provided for GenaiVectorsearch")
            return

        self.plugins = plugins

        if self.bot_config.SESSION_MANAGER_DEFAULT_PLUGIN_NAME is not None:
            self.logger.info(
                f"Setting default Genai Vector Search plugin to <{self.bot_config.SESSION_MANAGER_DEFAULT_PLUGIN_NAME}>")
            self.default_plugin = self.get_plugin(
                self.bot_config.SESSION_MANAGER_DEFAULT_PLUGIN_NAME)
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

        self.logger.error(f"SessionManager: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin

    @property
    def plugins(self) -> List[SessionManagerPluginBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[SessionManagerPluginBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin: SessionManagerPluginBase = self.get_plugin()
        plugin.plugin_name = value

    def generate_session_id(self, channel_id: str, thread_id: str, plugin_name=None) -> str:
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        return plugin.generate_session_id(channel_id, thread_id)

    async def create_session(self, channel_id: str, thread_id: str, start_time: Optional[str] = None, enriched: bool = False, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        return await plugin.create_session(channel_id, thread_id, start_time, enriched)

    async def load_session(self, session_id: str, plugin_name=None) -> Optional[EnrichedSession]:
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        return await plugin.load_session(session_id)

    async def save_session(self, session: EnrichedSession, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        await plugin.save_session(session)

    async def get_or_create_session(self, channel_id: str, thread_id: str, enriched: bool = False, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        return await plugin.get_or_create_session(channel_id, thread_id, enriched)

    def append_messages(self, messages: List[Dict], message: Dict, session_id: str, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin()
        plugin.append_messages(messages, message, session_id)

    async def add_user_interaction_to_message(self, session: EnrichedSession, message_index: int, interaction: Dict, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        await plugin.add_user_interaction_to_message(session, message_index, interaction)

    async def add_mind_interaction_to_message(self, session: EnrichedSession, message_index: int, interaction: Dict, plugin_name=None):
        plugin: SessionManagerPluginBase = self.get_plugin(plugin_name)
        await plugin.add_mind_interaction_to_message(session, message_index, interaction)
