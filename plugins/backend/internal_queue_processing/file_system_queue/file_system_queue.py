import os
import time
import json
import traceback
from typing import List, Optional, Tuple

from pydantic import BaseModel

from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager


class FileSystemQueueConfig(BaseModel):
    PLUGIN_NAME: str
    FILE_SYSTEM_QUEUE_DIRECTORY: str
    FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: str
    FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER: str


class FileSystemQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.logger = global_manager.logger
        self.global_manager = global_manager
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING["FILE_SYSTEM_QUEUE"]
        self.file_system_config = FileSystemQueueConfig(**config_dict)

        # Initialize queue containers to None
        self.message_queue_container = None
        self.internal_events_queue_container = None
        self.external_events_queue_container = None
        self.wait_queue_container = None

    @property
    def plugin_name(self):
        return "file_system_queue"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def messages_queue(self):
        return self.message_queue_container

    @property
    def internal_events_queue(self):
        return self.internal_events_queue_container

    @property
    def external_events_queue(self):
        return self.external_events_queue_container

    @property
    def wait_queue(self):
        return self.wait_queue_container

    def initialize(self):
        try:
            self.logger.debug("Initializing file system for queue management")
            self.root_directory = self.file_system_config.FILE_SYSTEM_QUEUE_DIRECTORY
            self.message_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER
            self.internal_events_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER
            self.external_events_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER
            self.wait_queue_container = self.file_system_config.FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER
            self.plugin_name = self.file_system_config.PLUGIN_NAME
            self.init_queues()
        except KeyError as e:
            self.logger.error(f"Missing configuration key: {str(e)}")

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
            except OSError as e:
                self.logger.error(f"Failed to create directory: {directory_path} - {str(e)}")
                raise

    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, message: str) -> None:
        """
        Adds a message to the queue.
        """
        message_id = f"{channel_id}_{thread_id}_{message_id}.txt"
        file_path = os.path.join(self.root_directory, data_container, message_id)

        try:
            self.logger.debug(f"Enqueuing message for channel '{channel_id}', thread '{thread_id}'.")
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(message)
            self.logger.info(f"Message successfully enqueued with ID '{message_id}'.")
        except Exception as e:
            self.logger.error(f"Failed to enqueue message: {str(e)}")

    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str) -> None:
        """
        Removes a message from the queue.
        """
        file_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        file_path = os.path.join(self.root_directory, data_container, file_name)

        self.logger.debug(f"Dequeuing message '{message_id}' for channel '{channel_id}', thread '{thread_id}'.")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.logger.debug(f"Message '{message_id}' removed successfully.")
            except Exception as e:
                self.logger.error(f"Failed to remove message: {str(e)}")
        else:
            self.logger.warning(f"Message '{message_id}' not found in queue.")

    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next message in the queue for a given channel/thread.
        """
        self.logger.info(f"Retrieving next message for channel '{channel_id}', thread '{thread_id}' after '{current_message_id}'.")

        try:
            queue_path = os.path.join(self.root_directory, data_container)
            files = os.listdir(queue_path)
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}_")]

            if not filtered_files:
                return None, None

            def extract_message_id(file_name: str) -> float:
                parts = file_name.split('_')
                return float(parts[2].replace('.txt', ''))

            current_timestamp = float(current_message_id)
            filtered_files.sort(key=extract_message_id)

            next_message_file = next((f for f in filtered_files if extract_message_id(f) > current_timestamp), None)

            if not next_message_file:
                return None, None

            file_path = os.path.join(queue_path, next_message_file)
            with open(file_path, 'r') as file:
                message_content = file.read()

            next_message_id = next_message_file.split('_')[-1].replace('.txt', '')

            return next_message_id, message_content

        except Exception as e:
            self.logger.error(f"Failed to retrieve next message: {str(e)}")
            return None, None

    async def get_all_messages(self, data_container: str, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves all messages for a given channel/thread.
        """
        self.logger.info(f"Retrieving all messages for channel '{channel_id}', thread '{thread_id}'.")

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
            self.logger.error(f"Failed to retrieve messages: {str(e)}")
            return []

    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are any older messages in the queue, excluding the current message.
        """
        self.logger.info(f"Checking for older messages in queue for channel '{channel_id}', thread '{thread_id}', excluding message_id '{current_message_id}'.")
        
        try:
            queue_path = os.path.join(self.root_directory, data_container)
            files = os.listdir(queue_path)
            
            # Filter files for the given channel_id and thread_id
            filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}")]
            
            # Exclude the current message file
            filtered_files = [f for f in filtered_files if current_message_id not in f]
            
            # Log the filtered files for debugging
            self.logger.debug(f"Filtered files excluding current message: {filtered_files}")
            
            return len(filtered_files) > 0
        
        except Exception as e:
            self.logger.error(f"Failed to check older messages: {str(e)}")
            return False

    async def clear_messages_queue(self, data_container: str, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel/thread.
        """
        self.logger.info(f"Clearing queue for channel '{channel_id}', thread '{thread_id}'.")

        queue_path = os.path.join(self.root_directory, data_container)
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
                        self.logger.info(f"Message '{file_path}' deleted successfully.")
                    except Exception as e:
                        self.logger.error(f"Failed to delete message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to clear queue: {str(e)}")
