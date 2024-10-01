import os
from typing import List, Optional, Tuple
from pydantic import BaseModel
from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager
import time
import uuid

LOG_PREFIX = "[FILE_SYSTEM_QUEUE]"

class FileSystemQueueConfig(BaseModel):
    PLUGIN_NAME: str
    FILE_SYSTEM_QUEUE_DIRECTORY: str
    FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_TTL: int
    FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_TTL: int
    FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL: int
    FILE_SYSTEM_QUEUE_WAIT_QUEUE_TTL: int


class FileSystemQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.logger = global_manager.logger
        self.global_manager = global_manager
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING["FILE_SYSTEM_QUEUE"]
        self.file_system_config = FileSystemQueueConfig(**config_dict)

        # Initialize queue containers and TTLs to None
        self._message_queue_container = None
        self._messages_queue_ttl = None
        self._internal_events_queue_container = None
        self._internal_events_queue_ttl = None
        self._external_events_queue_container = None
        self._external_events_queue_ttl = None
        self._wait_queue_container = None
        self._wait_queue_ttl = None        

    @property
    def plugin_name(self):
        return "file_system_queue"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def messages_queue(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER
    
    @messages_queue.setter
    def messages_queue(self, value):
        self._message_queue_container = value

    @property
    def messages_queue_ttl(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_TTL
    
    @messages_queue_ttl.setter
    def messages_queue_ttl(self, value):
        self._messages_queue_ttl = value

    @property
    def internal_events_queue(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER
    
    @internal_events_queue.setter
    def internal_events_queue(self, value):
        self._internal_events_queue_container = value

    @property
    def internal_events_queue_ttl(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_TTL
    
    @internal_events_queue_ttl.setter
    def internal_events_queue_ttl(self, value):
        self._internal_events_queue_ttl = value

    @property
    def external_events_queue(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER
    
    @external_events_queue.setter
    def external_events_queue(self, value):
        self._external_events_queue_container = value

    @property
    def external_events_queue_ttl(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL
    
    @external_events_queue_ttl.setter
    def external_events_queue_ttl(self, value):
        self._external_events_queue_ttl = value

    @property
    def wait_queue(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER
    
    @wait_queue.setter
    def wait_queue(self, value):
        self._wait_queue_container = value

    @property
    def wait_queue_ttl(self):
        return self.file_system_config.FILE_SYSTEM_QUEUE_WAIT_QUEUE_TTL
    
    @wait_queue_ttl.setter
    def wait_queue_ttl(self, value):
        self._wait_queue_ttl = value

    def initialize(self):
        try:
            self.logger.debug(f"{LOG_PREFIX} Initializing file system for queue management")
            self.root_directory = self.file_system_config.FILE_SYSTEM_QUEUE_DIRECTORY
            self.message_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER
            self.internal_events_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER
            self.external_events_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER
            self.wait_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER
            self.messages_queue_ttl = self.file_system_config.FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_TTL
            self.internal_events_queue_ttl = self.file_system_config.FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_TTL
            self.external_events_queue_ttl = self.file_system_config.FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL
            self.wait_queue_ttl = self.file_system_config.FILE_SYSTEM_QUEUE_WAIT_QUEUE_TTL
            self.plugin_name =self.file_system_config.PLUGIN_NAME
            self.init_queues()

        except KeyError as e:
            self.logger.error(f"{LOG_PREFIX} Missing configuration key: {str(e)}")

    def init_queues(self):
        containers = [
            self.message_queue_container,
            self.internal_events_queue_container,
            self.external_events_queue_container,
            self.wait_queue_container
        ]
        for container in containers:
            directory_path = os.path.join(self.root_directory, container)
            try:
                os.makedirs(directory_path, exist_ok=True)
                self.logger.info(f"{LOG_PREFIX} Queue directory initialized: {directory_path}")
            except OSError as e:
                self.logger.error(f"{LOG_PREFIX} Failed to create directory: {directory_path} - {str(e)}")
                raise

    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, message: str, guid: Optional[str] = None) -> None:
        """
        Adds a message to the queue with a unique GUID for each message.
        """
        # Generate a unique GUID for the message
        guid = guid or str(uuid.uuid4())
        
        # Update message_id to include the GUID
        message_file_name = f"{channel_id}_{thread_id}_{message_id}_{guid}.txt"
        file_path = os.path.join(self.root_directory, data_container, message_file_name)

        try:
            self.logger.debug(f"{LOG_PREFIX} Enqueuing message for channel '{channel_id}', thread '{thread_id}' with GUID '{guid}'.")
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(message)
            self.logger.info(f"{LOG_PREFIX} Message successfully enqueued with ID '{message_file_name}'.")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to enqueue message: {str(e)}")

            self.logger.error(f"{LOG_PREFIX} Failed to enqueue message: {str(e)}")

    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, guid: str) -> None:
        """
        Removes a message from the queue based on channel_id, thread_id, message_id, and guid.
        """
        file_name = f"{channel_id}_{thread_id}_{message_id}_{guid}.txt"
        file_path = os.path.join(self.root_directory, data_container, file_name)

        self.logger.debug(f"{LOG_PREFIX} Dequeuing message '{file_name}' for channel '{channel_id}', thread '{thread_id}'.")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.info(f"{LOG_PREFIX} Message '{file_name}' removed successfully.")
            except Exception as e:
                self.logger.error(f"{LOG_PREFIX} Failed to remove message: {str(e)}")
        else:
            self.logger.warning(f"{LOG_PREFIX} Message '{file_name}' not found in queue.")


    def extract_message_id(self, file_name: str) -> Optional[str]:
        """
        Extracts the message ID (timestamp) from a file name.
        The file name is expected to follow the format: <channel_id>_<thread_id>_<message_id>_<guid>.txt
        Returns the message ID as a string, or None if the file name is invalid.
        """
        try:
            parts = file_name.split('_')
            # The format should now have at least 4 parts: <channel_id>_<thread_id>_<message_id>_<guid>.txt
            if len(parts) < 4 or not parts[-1].endswith('.txt'):
                return None  # Invalid file name format
            # Return the message_id (third element), which is the actual timestamp or identifier
            return parts[2]
        except (ValueError, IndexError):
            return None
        
    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next message in the queue for a given channel/thread.
        """
        self.logger.info(f"{LOG_PREFIX} Retrieving next message for channel '{channel_id}', thread '{thread_id}' after '{current_message_id}'.")

        try:
            queue_path = os.path.join(self.root_directory, data_container)
            files = os.listdir(queue_path)
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}_")]

            if not filtered_files:
                return None, None

            current_timestamp = float(current_message_id)

            # Filter files with a valid message ID and sort them by timestamp
            filtered_files = [f for f in filtered_files if self.extract_message_id(f) is not None]
            filtered_files.sort(key=self.extract_message_id)

            # Find the next message after current_message_id
            next_message_file = next((f for f in filtered_files if self.extract_message_id(f) > current_timestamp), None)

            if not next_message_file:
                return None, None

            file_path = os.path.join(queue_path, next_message_file)
            with open(file_path, 'r', encoding='utf-8') as file:
                message_content = file.read()

            next_message_id = next_message_file.split('_')[-1].replace('.txt', '')

            return next_message_id, message_content

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to retrieve next message: {str(e)}")
            return None, None

    async def get_all_messages(self, data_container: str, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves all messages for a given channel/thread.
        """
        self.logger.info(f"{LOG_PREFIX} Retrieving all messages for channel '{channel_id}', thread '{thread_id}'.")

        try:
            queue_path = os.path.join(self.root_directory, data_container)
            files = os.listdir(queue_path)
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}_")]

            if not filtered_files:
                return []

            messages_content = []
            for file_name in filtered_files:
                file_path = os.path.join(queue_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    messages_content.append(file.read())

            return messages_content

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to retrieve messages: {str(e)}")
            return []

    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are any older messages in the queue, excluding the current message.
        """
        self.logger.info(f"{LOG_PREFIX} Checking for older messages in queue for channel '{channel_id}', thread '{thread_id}', excluding message_id '{current_message_id}'.")

        try:
            queue_path = os.path.join(self.root_directory, data_container)
            files = os.listdir(queue_path)

            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}")]
            filtered_files = [f for f in filtered_files if current_message_id not in f]

            self.logger.debug(f"{LOG_PREFIX} Filtered files excluding current message: {filtered_files}")

            return len(filtered_files) > 0

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to check older messages: {str(e)}")
            return False

    async def clear_messages_queue(self, data_container: str, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel/thread.
        """
        self.logger.info(f"{LOG_PREFIX} Clearing queue for channel '{channel_id}', thread '{thread_id}'.")

        queue_path = os.path.join(self.root_directory, data_container)
        if not os.path.exists(queue_path):
            self.logger.warning(f"{LOG_PREFIX} Queue path '{queue_path}' does not exist.")
            return

        try:
            files = os.listdir(queue_path)
            for file_name in files:
                if file_name.startswith(f"{channel_id}_{thread_id}_"):
                    file_path = os.path.join(queue_path, file_name)
                    try:
                        os.remove(file_path)
                        self.logger.info(f"{LOG_PREFIX} Message '{file_path}' deleted successfully.")
                    except Exception as e:
                        self.logger.error(f"{LOG_PREFIX} Failed to delete message: {str(e)}")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to clear queue: {str(e)}")

    def is_message_expired(self, file_name: str, ttl_seconds: int) -> bool:
        """
        Check if a message has expired based on the extracted message_id (timestamp) and the TTL.
        """
        message_timestamp = self.extract_message_id(file_name)
        
        if message_timestamp is None:
            return False  # If the timestamp can't be extracted, we assume the message is not expired

        try:
            message_timestamp = float(message_timestamp)  # Conversion en float
        except ValueError:
            self.logger.error(f"Invalid message timestamp in file name: {file_name}")
            return False

        current_time = time.time()
        return (current_time - message_timestamp) > ttl_seconds


    async def cleanup_expired_messages(self, data_container: str, channel_id: str, thread_id: str, ttl_seconds: int) -> None:
        """
        Cleans up expired messages for a specific thread/channel based on the TTL, taking GUID into account.
        """
        queue_path = os.path.join(self.root_directory, data_container)
        if not os.path.exists(queue_path):
            return

        files = os.listdir(queue_path)
        for file_name in files:
            if file_name.startswith(f"{channel_id}_{thread_id}_"):
                # Check if the message has expired (without considering GUID)
                if self.is_message_expired(file_name, ttl_seconds):
                    file_path = os.path.join(queue_path, file_name)
                    self.logger.info(f"{LOG_PREFIX} Removing expired message: {file_path}")
                    os.remove(file_path)


    async def clean_all_queues(self) -> None:
        """
        Cleans up all expired messages across all queues based on their TTL values.
        """
        ttl_mapping = {
            self.message_queue_container: self.messages_queue_ttl,
            self.internal_events_queue_container: self.internal_events_queue_ttl,
            self.external_events_queue_container: self.external_events_queue_ttl,
            self.wait_queue_container: self.wait_queue_ttl,
        }

        total_removed_files = 0  # Track the total number of removed files

        for queue_container, ttl_seconds in ttl_mapping.items():
            queue_path = os.path.join(self.root_directory, queue_container)
            if not os.path.exists(queue_path):
                self.logger.debug(f"{LOG_PREFIX} Queue path '{queue_path}' does not exist. Skipping.")
                continue

            files = os.listdir(queue_path)
            removed_files_count = 0  # Track removed files per queue

            for file_name in files:
                if self.is_message_expired(file_name, ttl_seconds):
                    file_path = os.path.join(queue_path, file_name)
                    self.logger.debug(f"{LOG_PREFIX} Removing expired message: {file_path}")
                    os.remove(file_path)
                    removed_files_count += 1

            self.logger.info(f"{LOG_PREFIX} Removed {removed_files_count} expired files from queue '{queue_container}'.")
            total_removed_files += removed_files_count

        self.logger.info(f"{LOG_PREFIX} Total removed expired files across all queues: {total_removed_files}.")

    async def clear_all_queues(self) -> None:
        """
        Clears all messages from all queues, regardless of TTL.
        """
        queue_containers = [
            self.message_queue_container,
            self.internal_events_queue_container,
            self.external_events_queue_container,
            self.wait_queue_container,
        ]

        total_removed_files = 0  # Track the total number of removed files

        for queue_container in queue_containers:
            queue_path = os.path.join(self.root_directory, queue_container)
            if not os.path.exists(queue_path):
                self.logger.debug(f"{LOG_PREFIX} Queue path '{queue_path}' does not exist. Skipping.")
                continue

            files = os.listdir(queue_path)
            removed_files_count = 0  # Track removed files per queue

            for file_name in files:
                file_path = os.path.join(queue_path, file_name)
                self.logger.debug(f"{LOG_PREFIX} Removing message: {file_path}")
                os.remove(file_path)
                removed_files_count += 1

            self.logger.info(f"{LOG_PREFIX} Removed {removed_files_count} files from queue '{queue_container}'.")
            total_removed_files += removed_files_count

        self.logger.info(f"{LOG_PREFIX} Total removed files across all queues: {total_removed_files}.")

