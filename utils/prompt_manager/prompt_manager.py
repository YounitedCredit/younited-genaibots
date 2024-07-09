from typing import List

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from utils.config_manager.config_manager import ConfigManager


class PromptManager:
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager = self.global_manager.plugin_manager
        self.internal_data_plugins: List[InternalDataProcessingBase] = self.plugin_manager.plugins['BACKEND']['INTERNAL_DATA_PROCESSING']
        self.config_manager: ConfigManager = global_manager.config_manager
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def initialize(self):
        self.prompt_container = self.backend_internal_data_processing_dispatcher.prompts
        self.core_prompt = await self.get_core_prompt()
        self.main_prompt = await self.get_main_prompt()

    async def get_sub_prompt(self, message_type):
        # Get the sub_prompts folder name from the configuration
        sub_prompts_folder = self.config_manager.get_config(['BOT_CONFIG', 'SUBPROMPTS_FOLDER'])
        sub_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(sub_prompts_folder, f"{message_type}.txt")
        if not sub_prompt:
            self.logger.error(f"Error while retrieving sub prompt: {message_type} is empty")
        return sub_prompt

    async def get_core_prompt(self):
        core_prompt_file = self.config_manager.get_config(['BOT_CONFIG', 'CORE_PROMPT'])
        core_prompt = []
        core_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(self.prompt_container, f"{core_prompt_file}.txt")

        if not core_prompt:
            self.logger.error("Error while retrieving core prompt: core prompt is empty")
        return core_prompt

    async def get_main_prompt(self):
        main_prompt_file = self.config_manager.get_config(['BOT_CONFIG', 'MAIN_PROMPT'])
        main_prompt = []
        main_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(self.prompt_container, f"{main_prompt_file}.txt")
        if not main_prompt:
            self.logger.error("Error while retrieving main prompt: main prompt is empty")
        return main_prompt
