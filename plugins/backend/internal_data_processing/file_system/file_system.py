import inspect
import json
import os
import traceback
from typing import List, NoReturn
import re
from pydantic import BaseModel

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.backend.pricing_data import PricingData
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager
import time
import os
import json
from typing import Optional, Tuple


class FileSystemConfig(BaseModel):
    PLUGIN_NAME: str
    FILE_SYSTEM_DIRECTORY: str
    FILE_SYSTEM_SESSIONS_CONTAINER: str
    FILE_SYSTEM_FEEDBACKS_CONTAINER: str
    FILE_SYSTEM_CONCATENATE_CONTAINER: str
    FILE_SYSTEM_PROMPTS_CONTAINER: str
    FILE_SYSTEM_COSTS_CONTAINER: str
    FILE_SYSTEM_PROCESSING_CONTAINER: str
    FILE_SYSTEM_ABORT_CONTAINER: str
    FILE_SYSTEM_VECTORS_CONTAINER: str
    FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER: str
    FILE_SYSTEM_SUBPROMPTS_CONTAINER: str
    FILE_SYSTEM_MESSAGES_QUEUE_CONTAINER: str

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
        self.feedbacks_container = None
        self.concatenate_container = None
        self.prompts_container = None
        self.costs_container = None
        self.processing_container = None
        self.abort_container = None
        self.vectors_container = None
        self.custom_actions_container = None
        self.subprompts_container = None
        self.message_queue_container = None

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
    
    @property
    def subprompts(self):
        # Implement the subprompts property
        return self.subprompts_container
    
    @property
    def messages_queue(self):
        # Implement the messages_queue property
        return self.message_queue_container

    def initialize(self):
        try:
            self.logger.debug("Initializing file system")
            self.root_directory = self.file_system_config.FILE_SYSTEM_DIRECTORY
            self.sessions_container = self.file_system_config.FILE_SYSTEM_SESSIONS_CONTAINER
            self.feedbacks_container = self.file_system_config.FILE_SYSTEM_FEEDBACKS_CONTAINER
            self.concatenate_container = self.file_system_config.FILE_SYSTEM_CONCATENATE_CONTAINER
            self.prompts_container = self.file_system_config.FILE_SYSTEM_PROMPTS_CONTAINER
            self.costs_container = self.file_system_config.FILE_SYSTEM_COSTS_CONTAINER
            self.processing_container = self.file_system_config.FILE_SYSTEM_PROCESSING_CONTAINER
            self.abort_container = self.file_system_config.FILE_SYSTEM_ABORT_CONTAINER
            self.vectors_container = self.file_system_config.FILE_SYSTEM_VECTORS_CONTAINER
            self.custom_actions_container = self.file_system_config.FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER
            self.subprompts_container = self.file_system_config.FILE_SYSTEM_SUBPROMPTS_CONTAINER
            self.message_queue_container = self.file_system_config.FILE_SYSTEM_MESSAGES_QUEUE_CONTAINER
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
            self.feedbacks_container,
            self.concatenate_container,
            self.prompts_container,
            self.costs_container,
            self.processing_container,
            self.abort_container,
            self.vectors_container,
            self.custom_actions_container,
            self.subprompts_container,
            self.message_queue_container
        ]
        for container in containers:
            directory_path = os.path.join(self.root_directory, container)
            try:
                os.makedirs(directory_path, exist_ok=True)
            except OSError as e:
                self.logger.error(f"Failed to create directory: {directory_path} - {str(e)}")
                raise

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

    async def enqueue_message(self, channel_id: str, thread_id: str, message_id: str, message: str) -> None:
        """
        Adds a message to the queue.
        The file is named using `channel_id`, `thread_id`, and a unique timestamp.
        """
        message_id = f"{channel_id}_{thread_id}_{message_id}.txt"
        file_path = os.path.join(self.root_directory, self.message_queue_container, message_id)

        try:
            # Log that we are attempting to add a message
            self.logger.info(f"Attempting to enqueue message for channel '{channel_id}', thread '{thread_id}'.")

            # Write the message to a queue file using UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(message)

            # Log success
            self.logger.info(f"Message successfully enqueued with ID '{message_id}'. Stored in file '{file_path}'.")
        except Exception as e:
            self.logger.error(f"Failed to enqueue the message for channel '{channel_id}', thread '{thread_id}': {str(e)}")


    async def dequeue_message(self, channel_id: str, thread_id: str, message_id: str) -> None:
        """
        Removes a message from the queue after it has been processed.
        """
        file_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        file_path = os.path.join(self.root_directory, self.message_queue_container, file_name)

        self.logger.info(f"Attempting to dequeue message '{message_id}' from channel '{channel_id}', thread '{thread_id}'.")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.info(f"Message '{message_id}' successfully removed from the queue. File '{file_path}' deleted.")
            except Exception as e:
                self.logger.error(f"Failed to remove message '{message_id}' from the queue: {str(e)}")
        else:
            self.logger.warning(f"Message '{message_id}' not found in the queue. No action taken.")

    async def get_next_message(self, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message for a `channel_id`, `thread_id` after `current_message_id`.
        Returns a tuple (next_message_id, message_content). If no message is found, returns (None, None).
        """
        self.logger.info(f"Checking for the next message in the queue for channel '{channel_id}', thread '{thread_id}' after message ID '{current_message_id}'.")

        try:
            # List all files in the queue directory
            queue_path = os.path.join(self.root_directory, self.message_queue_container)
            files = os.listdir(queue_path)

            # Filter files for the specific `channel_id` and `thread_id`
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}_")]
            self.logger.info(f"Found {len(filtered_files)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_files:
                self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
                return None, None

            # Regular expression to match the filename structure: {channel_id}_{thread_id}_{message_id}.txt
            timestamp_regex = re.compile(rf"{channel_id}_(\d+\.\d+)_(\d+\.\d+)\.txt")

            # Extract the message_id (which is a timestamp) from the filename using regex
            def extract_message_id(file_name: str) -> float:
                match = timestamp_regex.search(file_name)
                if match:
                    return float(match.group(2))  # Group 2 contains the message_id (the third part)
                else:
                    raise ValueError(f"Filename '{file_name}' does not match the expected format '{channel_id}_{thread_id}_<message_id>.txt'")

            # Get the timestamp of the current message
            current_timestamp = extract_message_id(f"{channel_id}_{thread_id}_{current_message_id}.txt")

            # Sort files by the message_id (third timestamp in the filename)
            filtered_files.sort(key=extract_message_id)

            # Find the next message based on the timestamp comparison
            next_message_file = next((f for f in filtered_files if extract_message_id(f) > current_timestamp), None)

            if not next_message_file:
                self.logger.info(f"No newer message found after message ID '{current_message_id}' for channel '{channel_id}', thread '{thread_id}'.")
                return None, None

            file_path = os.path.join(queue_path, next_message_file)

            # Read the content of the next message
            with open(file_path, 'r') as file:
                message_content = file.read()

            next_message_id = next_message_file.split('_')[-1].replace('.txt', '')

            self.logger.info(f"Next message retrieved: '{next_message_file}' with ID '{next_message_id}'.")
            return next_message_id, message_content

        except ValueError as ve:
            # Log the error with specific details about the bad filename format
            self.logger.error(f"ValueError during message retrieval: {ve}")
            raise

        except Exception as e:
            self.logger.error(f"Failed to retrieve the next message for channel '{channel_id}', thread '{thread_id}': {str(e)}")
            return None, None


    async def get_all_messages(self, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves the contents of all messages for a `channel_id` and `thread_id`.
        Returns a list of message contents.
        """
        self.logger.info(f"Retrieving all messages in the queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            # List all files in the queue directory
            queue_path = os.path.join(self.root_directory, self.message_queue_container)
            files = os.listdir(queue_path)

            # Filter files for the specific `channel_id` and `thread_id`
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}_")]
            self.logger.info(f"Found {len(filtered_files)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_files:
                self.logger.info(f"No messages found for channel '{channel_id}', thread '{thread_id}'.")
                return []

            # Read the content of each filtered message file using UTF-8 encoding
            messages_content = []
            for file_name in filtered_files:
                file_path = os.path.join(queue_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    message_content = file.read()
                    messages_content.append(message_content)

            self.logger.info(f"Retrieved {len(messages_content)} messages for channel '{channel_id}', thread '{thread_id}'.")
            return messages_content

        except Exception as e:
            self.logger.error(f"Failed to retrieve all messages for channel '{channel_id}', thread '{thread_id}': {str(e)}")
            return []
        
    async def has_older_messages(self, channel_id: str, thread_id: str) -> bool:
        """
        Checks if there are any older messages in the queue for a given channel_id and thread_id.
        Removes any messages older than QUEUED_MESSAGE_TTL seconds.
        """
        message_ttl = self.global_manager.bot_config.QUEUED_MESSAGE_TTL

        self.logger.info(f"Checking for older messages in channel '{channel_id}', thread '{thread_id}'")
        try:
            current_time = int(time.time())
            queue_path = os.path.join(self.root_directory, self.message_queue_container)
            files = os.listdir(queue_path)
            
            # Filter messages for the specific channel_id and thread_id
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}")]
            self.logger.info(f"Found {len(filtered_files)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_files:
                self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
                return False

            # Check for messages older than message_ttl
            updated_files = []
            for file_name in filtered_files:
                try:
                    # Extract the message_id (last part of the filename)
                    message_id = file_name.split('_')[-1].split('.')[0]
                    timestamp = float(message_id)  # Ensure message_id is a valid timestamp
                    time_difference = current_time - timestamp
                    
                    if time_difference > message_ttl:
                        self.logger.warning(f"Removed message '{file_name}' from queue as it is older than {message_ttl} seconds.")
                        # Dequeue the message properly by passing channel_id, thread_id, and message_id
                        await self.dequeue_message(channel_id=channel_id, thread_id=thread_id, message_id=message_id)
                    else:
                        updated_files.append(file_name)
                except ValueError:
                    self.logger.error(f"Invalid message file format: {file_name}, skipping.")
            
            # Return True if there are valid messages left in the queue after removing stale ones
            return len(updated_files) > 0
        
        except Exception as e:
            self.logger.error(f"Failed to check for older messages: {str(e)}")
            return False

    async def clear_messages_queue(self, channel_id: str, thread_id: str, plugin_name: Optional[str] = None) -> None:
        """
        Clears all messages in the queue for a given channel and thread.
        """
        plugin = self.get_plugin(plugin_name)
        self.logger.info(f"Clearing messages queue for channel '{channel_id}', thread '{thread_id}' through {plugin.plugin_name}.")
        await plugin.clear_messages_queue(channel_id=channel_id, thread_id=thread_id)

    async def clear_messages_queue(self, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel and thread.
        """
        self.logger.info(f"Clearing messages queue for channel '{channel_id}', thread '{thread_id}'.")

        queue_path = os.path.join(self.root_directory, self.message_queue_container)
        if not os.path.exists(queue_path):
            self.logger.warning(f"Queue path '{queue_path}' does not exist.")
            return

        try:
            files = os.listdir(queue_path)
            for file_name in files:
                if file_name.startswith(f"{channel_id}_{thread_id}_"):
                    file_path = os.path.join(queue_path, file_name)
                    try:
                        os.remove(file_path)
                        self.logger.info(f"Message file '{file_path}' successfully deleted.")
                    except Exception as e:
                        self.logger.error(f"Failed to delete message file '{file_path}': {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to clear messages queue for channel '{channel_id}', thread '{thread_id}': {str(e)}")