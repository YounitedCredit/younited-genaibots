from pathlib import Path
from typing import List

from core.action_interactions.action_interactions_handler import (
    ActionInteractionsHandler,
)
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.genai_interactions.genai_interactions_image_generator_dispatcher import (
    GenaiInteractionsImageGeneratorDispatcher,
)
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.genai_interactions.genai_interactions_text_dispatcher import (
    GenaiInteractionsTextDispatcher,
)
from core.genai_interactions.genai_vectorsearch_dispatcher import GenaiVectorsearch
from core.user_interactions.user_interactions_behavior_base import (
    UserInteractionsBehaviorBase,
)
from core.user_interactions.user_interactions_behavior_dispatcher import (
    UserInteractionsBehaviorsDispatcher,
)
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from utils.config_manager.config_manager import ConfigManager
from utils.config_manager.config_model import BotConfig
from utils.logging.logger_loader import setup_logger_and_tracer
from utils.prompt_manager.prompt_manager import PromptManager


class GlobalManager:
    def __init__(self, app):
        from utils.plugin_manager.plugin_manager import PluginManager
        self.config_manager = ConfigManager(self)

        self.base_directory = Path(__file__).parent.parent.joinpath('plugins')
        self.logger, self.tracer = setup_logger_and_tracer(self)

        self.logger.debug("Initializing plugin manager and main handlers...")

        self.plugin_manager = PluginManager(self.base_directory, self)
        self.available_actions = {}

        self.logger.info("Plugin manager and main handlers initialized.")

        bot_config_dict = self.config_manager.config_model.BOT_CONFIG
        self.bot_config : BotConfig = bot_config_dict

        self.logger.info("Dispatchers creation...")
        self.backend_internal_data_processing_dispatcher = BackendInternalDataProcessingDispatcher(self)
        self.genai_interactions_text_dispatcher = GenaiInteractionsTextDispatcher(self)
        self.genai_image_generator_dispatcher = GenaiInteractionsImageGeneratorDispatcher(self)
        self.genai_vectorsearch_dispatcher = GenaiVectorsearch(self)
        self.user_interactions_dispatcher = UserInteractionsDispatcher(self)
        self.user_interactions_behavior_dispatcher = UserInteractionsBehaviorsDispatcher(self)

        self.logger.info("Loading plugins...")
        self.plugin_manager.load_plugins()        

        backend_internal_data_processing_plugins: List[InternalDataProcessingBase] = self.plugin_manager.get_plugin_by_category(
            "BACKEND", "INTERNAL_DATA_PROCESSING")
        user_interactions_plugins: List[UserInteractionsPluginBase] = self.plugin_manager.get_plugin_by_category(
            "USER_INTERACTIONS")
        genai_interactions_text_plugins: List[GenAIInteractionsPluginBase] = self.plugin_manager.get_plugin_by_category(
            "GENAI_INTERACTIONS", "TEXT")
        genai_image_generator_plugins : List[GenAIInteractionsPluginBase] = self.plugin_manager.get_plugin_by_category(
            "GENAI_INTERACTIONS", "IMAGE")
        vector_search_plugins : List[GenAIInteractionsPluginBase] = self.plugin_manager.get_plugin_by_category(
            "GENAI_INTERACTIONS", "VECTOR_SEARCH")
        user_interactions_behavior_plugins : List[UserInteractionsBehaviorBase] = self.plugin_manager.get_plugin_by_category(
            "USER_INTERACTIONS_BEHAVIORS")

        # Initialize dispatchers
        self.logger.info("Initializing dispatchers...")
        self.user_interactions_dispatcher.initialize(user_interactions_plugins)
        self.genai_interactions_text_dispatcher.initialize(genai_interactions_text_plugins)
        self.backend_internal_data_processing_dispatcher.initialize(backend_internal_data_processing_plugins)
        self.genai_image_generator_dispatcher.initialize(genai_image_generator_plugins)
        self.genai_vectorsearch_dispatcher.initialize(vector_search_plugins)
        self.user_interactions_behavior_dispatcher.initialize(user_interactions_behavior_plugins)

        self.logger.debug("Initializing plugins...")
        self.plugin_manager.initialize_plugins()
        self.logger.info("Plugins loaded.")

        self.logger.debug("Creating routes...")
        self.plugin_manager.intialize_routes(app)
        self.logger.info("Routes created.")

        self.action_interactions_handler = ActionInteractionsHandler(self)

        
        self.logger.debug("Prompt manager initialization...")
        self.prompt_manager = PromptManager(self)
        self.logger.info("Prompt manager loaded.")

    def get_plugin(self, category, subcategory):
        return self.plugin_manager.get_plugin_by_category(category, subcategory)

    def register_plugin_actions(self, plugin_name, actions):
        # Store the available actions for the plugin
        self.available_actions[plugin_name] = actions

    def get_action(self, action_name):
        for package, actions in self.available_actions.items():
            for action_class_name, action_class in actions.items():
                if action_name == action_class_name:
                    return action_class
        self.logger.error(f"No plugin found containing action name '{action_name}'")
