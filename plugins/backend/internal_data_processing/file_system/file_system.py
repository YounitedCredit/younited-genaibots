import inspect
import json
import os
import traceback
from typing import NoReturn

from pydantic import BaseModel

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.backend.pricing_data import PricingData
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager


class FileSystemConfig(BaseModel):
    PLUGIN_NAME: str
    FILE_SYSTEM_DIRECTORY: str
    FILE_SYSTEM_SESSIONS_CONTAINER: str
    FILE_SYSTEM_MESSAGES_CONTAINER: str
    FILE_SYSTEM_FEEDBACKS_CONTAINER: str
    FILE_SYSTEM_CONCATENATE_CONTAINER: str
    FILE_SYSTEM_PROMPTS_CONTAINER: str
    FILE_SYSTEM_COSTS_CONTAINER: str
    FILE_SYSTEM_PROCESSING_CONTAINER: str
    FILE_SYSTEM_ABORT_CONTAINER: str
    FILE_SYSTEM_VECTORS_CONTAINER: str
    FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER: str

class FileSystemPlugin(InternalDataProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.logger = global_manager.logger
        self.global_manager = global_manager
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING["FILE_SYSTEM"]
        self.file_system_config = FileSystemConfig(**config_dict)

        # Set the variables to None
        self.plugin_name = None
        self.root_directory = None
        self.sessions_container = None
        self.messages_container = None
        self.feedbacks_container = None
        self.concatenate_container = None
        self.prompts_container = None
        self.costs_container = None
        self.processing_container = None
        self.abort_container = None
        self.vectors_container = None
        self.custom_actions_container = None

    @property
    def plugin_name(self):
        return "file_sytem"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def sessions(self):
        # Implement the sessions property
        return self.sessions_container

    @property
    def messages(self):
        # Implement the messages property
        return self.messages_container

    @property
    def feedbacks(self):
        # Implement the feedbacks property
        return self.feedbacks_container

    @property
    def concatenate(self):
        # Implement the concatenate property
        return self.concatenate_container

    @property
    def prompts(self):
        # Implement the prompts property
        return self.prompts_container

    @property
    def costs(self):
        # Implement the costs property
        return self.costs_container

    @property
    def processing(self):
        # Implement the costs property
        return self.processing_container

    @property
    def abort(self):
        # Implement the costs property
        return self.abort_container

    @property
    def vectors(self):
        # Implement the vectors property
        return self.vectors_container

    @property
    def custom_actions(self):
        # Implement the custom_actions property
        return self.custom_actions_container

    def initialize(self):
        try:
            self.logger.debug("Initializing file system")
            self.root_directory = self.file_system_config.FILE_SYSTEM_DIRECTORY
            self.sessions_container = self.file_system_config.FILE_SYSTEM_SESSIONS_CONTAINER
            self.messages_container = self.file_system_config.FILE_SYSTEM_MESSAGES_CONTAINER
            self.feedbacks_container = self.file_system_config.FILE_SYSTEM_FEEDBACKS_CONTAINER
            self.concatenate_container = self.file_system_config.FILE_SYSTEM_CONCATENATE_CONTAINER
            self.prompts_container = self.file_system_config.FILE_SYSTEM_PROMPTS_CONTAINER
            self.costs_container = self.file_system_config.FILE_SYSTEM_COSTS_CONTAINER
            self.processing_container = self.file_system_config.FILE_SYSTEM_PROCESSING_CONTAINER
            self.abort_container = self.file_system_config.FILE_SYSTEM_ABORT_CONTAINER
            self.vectors_container = self.file_system_config.FILE_SYSTEM_VECTORS_CONTAINER
            self.custom_actions_container = self.file_system_config.FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER
            self.plugin_name = self.file_system_config.PLUGIN_NAME
            self.init_shares()
        except KeyError as e:
            self.logger.exception(f"Missing configuration key: {str(e)}")

    def validate_request(self, request):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    def handle_request(self, request):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    def init_shares(self):
        containers = [
            self.sessions_container,
            self.messages_container,
            self.feedbacks_container,
            self.concatenate_container,
            self.prompts_container,
            self.costs_container,
            self.processing_container,
            self.abort_container,
            self.vectors_container,
            self.custom_actions_container
        ]
        for container in containers:
            directory_path = os.path.join(self.root_directory, container)
            os.makedirs(directory_path, exist_ok=True)

    def append_data(self, container_name: str, data_identifier: str, data: str) -> NoReturn:
        # Construct the full path to the file
        file_path = os.path.join(self.root_directory, container_name, data_identifier)

        try:
            # Open the file in append mode
            with open(file_path, 'a') as file:
                # Write the data to the file
                file.write(data)
            self.logger.info("Data appended to the file.")
        except IOError as e:
            # Log an error message if an IOError occurs (e.g., if the file could not be opened)
            self.logger.error(f"Failed to append data to the file: {e}")

    async def read_data_content(self, data_container, data_file):
        self.logger.debug(f"Reading data content from {data_file} in {data_container}")
        file_path = os.path.join(self.root_directory, data_container, data_file)
        if os.path.exists(file_path):
            try:
                # Utiliser 'errors="ignore"' pour ignorer les caractères non valides
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    data = file.read()
                self.logger.debug("Data successfully read")
                return data
            except UnicodeDecodeError as e:
                self.logger.error(f"Unicode decode error: {str(e)}")
            except Exception as e:
                self.logger.error(f"Failed to read file: {str(e)}")
                return None
        else:
            self.logger.debug(f"File not found: {data_file}")
            return None

    async def write_data_content(self, data_container, data_file, data):
        self.logger.debug(f"Writing data content to {data_file} in {data_container}")
        file_path = os.path.join(self.root_directory, data_container, data_file)
        try:
            with open(file_path, 'w') as file:
                file.write(data)
            self.logger.debug("Data successfully written to file")
        except Exception:
            error_traceback = traceback.format_exc()
            self.logger.exception(f"Failed to write to file: {str(error_traceback)}")

    async def store_unmentioned_messages(self, channel_id, thread_id, message):
        self.logger.debug(f"Storing unmentioned messages for channel {channel_id}, thread {thread_id}")
        file_path = os.path.join(self.root_directory,self.messages_container, f"unmentioned_messages_{channel_id}_{thread_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    messages = json.load(file)
                self.logger.debug("Existing messages successfully retrieved")
            except Exception as e:
                self.logger.error(f"Failed to read file: {str(e)}")
                messages = []
        else:
            self.logger.debug("No existing messages found, initializing empty list")
            messages = []

        messages.append(message)

        try:
            with open(file_path, 'w') as file:
                json.dump(messages, file)
            self.logger.debug("Message successfully stored")
        except Exception as e:
            self.logger.error(f"Failed to write to file: {str(e)}")

    async def retrieve_unmentioned_messages(self, channel_id, thread_id):
        self.logger.debug(f"Retrieving unmentioned messages for channel {channel_id}, thread {thread_id}")
        file_path = os.path.join(self.root_directory,self.messages_container, f"unmentioned_messages_{channel_id}_{thread_id}.json")

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    file_content = file.read()
                os.remove(file_path)  # Delete the file after retrieving the content
                messages = json.loads(file_content)
                self.logger.debug("Messages successfully retrieved and file deleted")
                return messages
            except Exception as e:
                self.logger.error(f"Failed to retrieve or delete messages: {str(e)}")
                return []
        else:
            self.logger.warning("File not found")
            return []

    async def remove_data_content(self, data_container, data_file):
        self.logger.debug(f"Removing data content from {data_file} in {data_container}")
        file_path = os.path.join(self.root_directory, data_container, data_file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.debug("File successfully deleted")
            except Exception as e:
                self.logger.error(f"Failed to delete file: {str(e)}")
                return None
        else:
            self.logger.debug(f"File not found: {data_file}")
            return None

    async def update_pricing(self, container_name, datafile_name, pricing_data):
        self.logger.debug(f"Updating pricing in file {datafile_name} in container {container_name}")
        file_path = os.path.join(self.root_directory, container_name, datafile_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    data = PricingData(**json.load(file))
                self.logger.debug("Existing pricing data retrieved")
            except Exception as e:
                self.logger.error(f"Failed to read file: {str(e)}")
                data = PricingData()
        else:
            self.logger.debug("No existing pricing data found, initializing new pricing structure")
            data = PricingData()

        # Update cumulative costs with current costs
        data.total_tokens += pricing_data.total_tokens
        data.prompt_tokens += pricing_data.prompt_tokens
        data.completion_tokens += pricing_data.completion_tokens
        data.total_cost += pricing_data.total_cost
        data.input_cost += pricing_data.input_cost
        data.output_cost += pricing_data.output_cost
        self.logger.debug(f"Updated pricing data: {data.__dict__}")

        try:
            with open(file_path, 'w') as file:
                json.dump(data.__dict__, file)
            self.logger.debug("Pricing update completed")
        except Exception as e:
            self.logger.error(f"Failed to write to file: {str(e)}")

        return data

    async def update_prompt_system_message(self, channel_id, thread_id, message):
        self.logger.debug(f"Updating prompt system message for channel {channel_id}, thread {thread_id}")
        file_path = os.path.join(self.root_directory, self.sessions, f"{channel_id}-{thread_id}.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    session = json.load(file)
                self.logger.debug("Session string parsed into JSON")
            except Exception as e:
                self.logger.error(f"Failed to read file: {str(e)}")
                return
        else:
            self.logger.error(f"Session data not found for file {file_path}")
            return

        updated = False
        for obj in session:
            if obj.get('role') == 'system':
                self.logger.info("Found system role, updating content")
                obj['content'] = message
                updated = True
                break

        if not updated:
            self.logger.warning("System role not found in session JSON")
            return

        try:
            with open(file_path, 'w') as file:
                json.dump(session, file)
            self.logger.info("Prompt system message update completed successfully")
        except Exception as e:
            self.logger.error(f"Failed to write to file: {str(e)}")

    async def list_container_files(self, container_name):
        try:
            file_names = []
            container_path = os.path.join(self.root_directory, container_name)  # Calculate the container path
            for file in os.listdir(container_path):
                if os.path.isfile(os.path.join(container_path, file)):
                    file_name_without_extension = os.path.splitext(file)[0]
                    file_names.append(file_name_without_extension)
            return file_names
        except Exception as e:
            self.logger.error(f"An error occurred while listing files: {e}")
            return []

    async def update_session(self, data_container, data_file, role, content):
        self.logger.debug(f"Updating session for file {data_file} in container {data_container}")
        file_path = os.path.join(self.root_directory, data_container, data_file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                self.logger.debug("JSON content successfully parsed")
            except Exception as e:
                self.logger.error(f"Failed to read file: {str(e)}")
                return
        else:
            data = []  # Default to an empty list

        data.append({"role": role, "content": content})
        self.logger.debug(f"Appended new role/content: {role}/{content}")

        try:
            with open(file_path, 'w') as file:
                json.dump(data, file)
            self.logger.debug("Session update completed")
        except Exception as e:
            self.logger.error(f"Failed to write to file: {str(e)}")
