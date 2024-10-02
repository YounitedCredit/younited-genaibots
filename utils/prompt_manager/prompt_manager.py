import os
from typing import List

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from utils.config_manager.config_manager import ConfigManager


class PromptManager:
    def __init__(self, global_manager):
        """
        Initialize the PromptManager with access to the global_manager and necessary plugins.
        """
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager = self.global_manager.plugin_manager
        self.internal_data_plugins: List[InternalDataProcessingBase] = self.plugin_manager.plugins['BACKEND']['INTERNAL_DATA_PROCESSING']
        self.config_manager: ConfigManager = global_manager.config_manager
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

        # New: Manage whether prompts are loaded from backend or locally
        self.load_prompts_from_backend = self.global_manager.bot_config.LOAD_PROMPTS_FROM_BACKEND
        self.local_prompts_path = self.global_manager.bot_config.LOCAL_PROMPTS_PATH
        self.local_subprompts_path = self.global_manager.bot_config.LOCAL_SUBPROMPTS_PATH

        # Log initialization
        self.logger.info("PromptManager initialized. Using backend for prompts: %s", self.load_prompts_from_backend)

    async def initialize(self):
        """
        Initialize core and main prompts during startup by loading them from either backend or local files.
        """
        self.logger.info("Initializing core and main prompts...")
        self.prompt_container = self.backend_internal_data_processing_dispatcher.prompts
        self.core_prompt = await self.get_core_prompt()
        self.main_prompt = await self.get_main_prompt()
        self.logger.info("Core and main prompts initialized.")

    async def get_sub_prompt(self, message_type: str):
        """
        Retrieve a specific subprompt based on message type.
        This method checks whether the subprompts are managed via backend or locally.
        :param message_type: The message type used to identify the subprompt file (e.g., "error", "info").
        :return: The content of the subprompt file.
        """
        self.logger.info("Fetching subprompt for message type: %s", message_type)
        if self.load_prompts_from_backend:
            sub_prompts_folder = self.backend_internal_data_processing_dispatcher.subprompts
            sub_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(sub_prompts_folder, f"{message_type}.txt")
            self.logger.info("Subprompt '%s' loaded from backend.", message_type)
        else:
            sub_prompt = self._read_local_subprompt(message_type)
            if sub_prompt:
                self.logger.info("Subprompt '%s' loaded from local files.", message_type)
            else:
                self.logger.error(f"Error while retrieving sub prompt: {message_type} is empty")

        return sub_prompt

    async def get_core_prompt(self):
        """
        Load the core prompt either from the backend or local path based on configuration.
        :return: The content of the core prompt file.
        """
        core_prompt_file = self.config_manager.get_config(['BOT_CONFIG', 'CORE_PROMPT'])
        self.logger.info("Fetching core prompt from %s...", "backend" if self.load_prompts_from_backend else "local")

        if self.load_prompts_from_backend:
            core_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(self.prompt_container, f"{core_prompt_file}.txt")
            self.logger.info("Core prompt loaded from backend.")
        else:
            core_prompt = self._read_local_prompt(f"{core_prompt_file}.txt")
            if core_prompt:
                self.logger.info("Core prompt loaded from local path.")
            else:
                self.logger.error("Error while retrieving core prompt: core prompt is empty")

        return core_prompt

    async def get_main_prompt(self, main_prompt_file: str = None):
        """
        Load the main prompt either from the backend or local path based on configuration.
        :return: The content of the main prompt file.
        """

        if main_prompt_file is None:
            main_prompt_file = self.config_manager.get_config(['BOT_CONFIG', 'MAIN_PROMPT'])
            
        self.logger.info("Fetching main prompt from %s...", "backend" if self.load_prompts_from_backend else "local")

        if self.load_prompts_from_backend:
            main_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(self.prompt_container, f"{main_prompt_file}.txt")
            self.logger.info("Main prompt loaded from backend.")
        else:
            main_prompt = self._read_local_prompt(f"{main_prompt_file}.txt")
            if main_prompt:
                self.logger.info("Main prompt loaded from local path.")
            else:
                self.logger.error("Error while retrieving main prompt: main prompt is empty")

        return main_prompt

    # ============================================
    # Helper Methods for Local File Handling
    # ============================================

    def _read_local_prompt(self, file_name: str):
        """
        Helper function to read a local prompt file by name.
        :param file_name: The name of the prompt file (e.g., core_prompt.txt).
        :return: The content of the file, or None if not found.
        """
        file_path = os.path.join(self.local_prompts_path, file_name)
        self.logger.info("Attempting to read local prompt file: %s", file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:  # Specify UTF-8 encoding
                return file.read()
        except FileNotFoundError:
            self.logger.error(f"Local prompt file not found: {file_path}")
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"Error decoding the file {file_path}: {str(e)}")
            return None

    def _read_local_subprompt(self, message_type: str):
        """
        Helper function to read a subprompt from the local subprompts directory.
        :param message_type: The type of subprompt (e.g., "error", "info").
        :return: The content of the subprompt file, or None if not found.
        """
        file_path = os.path.join(self.local_subprompts_path, f"{message_type}.txt")
        self.logger.info("Attempting to read local subprompt file: %s", file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:  # Specify UTF-8 encoding
                return file.read()
        except FileNotFoundError:
            self.logger.error(f"Local subprompt file not found: {file_path}")
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"Error decoding the file {file_path}: {str(e)}")
            return None
