from pathlib import Path

from core.action_interactions.action_interactions_plugin_base import (
    ActionInteractionsPluginBase,
)


class MainActionsPlugin(ActionInteractionsPluginBase):
    def initialize(self):
        # Create a collection of available actions
        base_directory = Path(__file__).parent
        actions_path = base_directory / 'actions'
        self.load_actions(str(actions_path))
        self.plugin_name = self.__class__.__name__.replace("Plugin", "")

    @property
    def plugin_name(self):
        return "main_actions"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value
