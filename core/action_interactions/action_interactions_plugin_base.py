import importlib
import inspect
import pkgutil
import sys
from abc import ABC
from pathlib import Path

from core.action_interactions.action_base import ActionBase
from core.global_manager import GlobalManager
from core.plugin_base import PluginBase
from utils.plugin_manager.plugin_manager import PluginManager


class ActionInteractionsPluginBase(PluginBase, ABC):
    def __init__(self, global_manager: GlobalManager ):
        super().__init__(global_manager)
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.logger = global_manager.logger
        self.available_actions = {}  # Initialize available actions

    def initialize(self):
        base_directory = Path(__file__).parent
        sys.path.insert(0, str(base_directory))
        actions_path = base_directory / "actions"
        self.load_actions(actions_path)  # Load actions
        self.global_manager.register_plugin_actions(self.__class__.__name__, self.available_actions)

    def load_actions(self, actions_path):
        root_directory = Path(__file__).resolve().parent.parent.parent
        loaded_actions = []

        for _, module_name, _ in pkgutil.iter_modules([actions_path]):
            module = self._import_module(actions_path, module_name, root_directory)
            if module:
                self._process_module(module, loaded_actions)

        self._log_loaded_actions(loaded_actions)

    def _import_module(self, actions_path, module_name, root_directory):
        module_path = Path(actions_path) / module_name
        relative_path = module_path.relative_to(root_directory)
        module_name = str(relative_path).replace('/', '.').replace('\\', '.')
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")
            return None

    def _process_module(self, module, loaded_actions):
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if self._is_valid_action_class(cls):
                self._add_action_class(cls, loaded_actions)

    def _is_valid_action_class(self, cls):
        return issubclass(cls, ActionBase) and cls is not ActionBase

    def _add_action_class(self, cls, loaded_actions):

        try:
            if __package__ not in self.global_manager.available_actions:
                self.global_manager.available_actions[__package__] = {}

            self.global_manager.available_actions[__package__][cls.__name__] = cls(self.global_manager)
            loaded_actions.append(cls.__name__)

        except Exception as e:
            self.logger.error(f"Failed to instantiate action class {cls.__name__}: {e}")

    def _log_loaded_actions(self, loaded_actions):
        self.logger.debug(f"Actions loaded from plugin {self.__class__.__name__}: <{', '.join(loaded_actions)}>")

    def validate_actions(self):
        for action in self._Actions:
            action_class = getattr(self, f'{action.value}Action', None)
            if action_class is not None and issubclass(action_class, ActionBase):
                continue
            else:
                raise ValueError(f"No valid action class found for action '{action.value}'")

    async def execute_action(self, action_name: str, item):
        action_class = {}
        action_class = getattr(self, f'{action_name}Action', None)
        if action_class is not None and issubclass(action_class, ActionBase):
            action_instance = action_class()
            return action_instance.execute(item)
        else:
            raise ValueError(f"No valid action class found for action '{action_name}'")
