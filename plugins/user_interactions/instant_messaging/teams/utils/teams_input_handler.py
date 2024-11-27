from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager


class TeamsInputHandler:
    def __init__(self, global_manager: GlobalManager, teams_config):
        from ..teams import TeamsConfig
        self.global_manager = global_manager
        self.logger = global_manager.logger
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        self.teams_config: TeamsConfig = teams_config

        if self.teams_config is None:
            self.logger.error("No 'TEAMS' configuration found in 'USER_INTERACTIONS_PLUGINS'")
            return

        self.TEAMS_AUTHORIZED_CHANNELS = set(self.teams_config.TEAMS_AUTHORIZED_CHANNELS)
        self.TEAMS_BOT_USER_ID = self.teams_config.TEAMS_BOT_USER_ID
