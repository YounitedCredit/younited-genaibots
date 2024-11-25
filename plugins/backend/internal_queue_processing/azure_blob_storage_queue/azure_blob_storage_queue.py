import logging
import time
import uuid
from typing import List, Optional, Tuple

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from pydantic import BaseModel

from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager

AZURE_BLOB_STORAGE_QUEUE = "AZURE_BLOB_STORAGE_QUEUE"
LOG_PREFIX = "[AZURE_BLOB_QUEUE]"

class AzureBlobStorageConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING: str
    AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL: int
    AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL: int
    AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL: int
    AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL: int

class AzureBlobStorageQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        self.logger = global_manager.logger
        super().__init__(global_manager)
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING[AZURE_BLOB_STORAGE_QUEUE]
        self.azure_blob_storage_config = AzureBlobStorageConfig(**config_dict)
        self.plugin_name = None

    def initialize(self):
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("azure.storage.blob").setLevel(logging.WARNING)
        self.logger.debug(f"{LOG_PREFIX} Initializing Azure Blob Storage connection")
        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING,
                credential=credential
            )
            self.logger.info(f"{LOG_PREFIX} BlobServiceClient successfully created")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to create BlobServiceClient: {str(e)}")
            raise
        self.init_containers()

    @property
    def plugin_name(self):
        return "azure_blob_storage_queue"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def messages_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER

    @property
    def messages_queue_ttl(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL

    @property
    def internal_events_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER

    @property
    def internal_events_queue_ttl(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL

    @property
    def external_events_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER

    @property
    def external_events_queue_ttl(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL

    @property
    def wait_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER

    @property
    def wait_queue_ttl(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL

    def init_containers(self):
        container_names = [
            self.messages_queue,
            self.internal_events_queue,
            self.external_events_queue,
            self.wait_queue
        ]
        for container in container_names:
            try:
                container_client = self.blob_service_client.get_container_client(container)
                if not container_client.exists():
                    container_client.create_container()
                    self.logger.info(f"{LOG_PREFIX} Created container: {container}")
                else:
                    self.logger.info(f"{LOG_PREFIX} Container already exists: {container}")
            except Exception as e:
                self.logger.error(f"{LOG_PREFIX} Failed to create container {container}: {str(e)}")

    def extract_message_id(self, blob_name: str) -> Optional[float]:
        try:
            parts = blob_name.split('_')
            return float(parts[2].replace('.txt', ''))
        except (ValueError, IndexError):
            self.logger.warning(f"{LOG_PREFIX} Failed to extract message ID from blob name: {blob_name}")
            return None

    def is_message_expired(self, blob_name: str, ttl_seconds: int) -> bool:
        message_timestamp = self.extract_message_id(blob_name)
        if message_timestamp is None:
            self.logger.warning(f"{LOG_PREFIX} Cannot determine expiration for blob: {blob_name}")
            return False

        current_time = time.time()
        expired = (current_time - message_timestamp) > ttl_seconds
        if expired:
            self.logger.info(f"{LOG_PREFIX} Message {blob_name} has expired. TTL: {ttl_seconds} seconds.")
        return expired

    async def cleanup_expired_messages(self, data_container: str, channel_id: str, thread_id: str, ttl_seconds: int) -> None:
        """
        Cleans up expired messages for a specific thread/channel based on the TTL, taking GUID into account.
        """
        self.logger.info(f"{LOG_PREFIX} Cleaning up expired messages for channel '{channel_id}', thread '{thread_id}' with TTL '{ttl_seconds}' seconds.")
        container_client = self.blob_service_client.get_container_client(data_container)
        blobs = list(container_client.list_blobs())

        for blob in blobs:
            if blob.name.startswith(f"{channel_id}_{thread_id}_"):
                if self.is_message_expired(blob.name, ttl_seconds):
                    blob_client = self.blob_service_client.get_blob_client(data_container, blob.name)
                    self.logger.info(f"{LOG_PREFIX} Removing expired message: {blob.name}")
                    try:
                        blob_client.delete_blob()
                        self.logger.info(f"{LOG_PREFIX} Expired message removed: {blob.name}")
                    except Exception as e:
                        self.logger.error(f"{LOG_PREFIX} Failed to delete expired message {blob.name}: {str(e)}")

    async def clean_all_queues(self) -> None:
        """
        Cleans up all expired messages across all Azure Blob Storage queues based on their TTL values.
        """
        ttl_mapping = {
            self.messages_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL,
            self.internal_events_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL,
            self.external_events_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL,
            self.wait_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL,
        }

        total_removed_files = 0  # Track the total number of removed files

        for queue_container, ttl_seconds in ttl_mapping.items():
            self.logger.info(f"{LOG_PREFIX} Cleaning up expired messages in container: {queue_container} with TTL: {ttl_seconds} seconds.")
            container_client = self.blob_service_client.get_container_client(queue_container)
            blobs = list(container_client.list_blobs())

            removed_files_count = 0  # Track removed files per queue

            for blob in blobs:
                if self.is_message_expired(blob.name, ttl_seconds):
                    blob_client = self.blob_service_client.get_blob_client(queue_container, blob.name)
                    self.logger.debug(f"{LOG_PREFIX} Removing expired message: {blob.name}")
                    try:
                        blob_client.delete_blob()
                        self.logger.info(f"{LOG_PREFIX} Deleted expired message: {blob.name}")
                        removed_files_count += 1
                    except Exception as e:
                        self.logger.error(f"{LOG_PREFIX} Failed to delete expired message {blob.name}: {str(e)}")

            self.logger.info(f"{LOG_PREFIX} Removed {removed_files_count} expired files from queue '{queue_container}'.")
            total_removed_files += removed_files_count

        self.logger.info(f"{LOG_PREFIX} Total removed expired files across all queues: {total_removed_files}.")


    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, message: str, guid: Optional[str] = None) -> None:
        """
        Adds a message to the queue with a unique GUID for each message.
        """
        # Generate a unique GUID for the message
        guid = guid or str(uuid.uuid4())

        # Update message_id to include the GUID
        blob_name = f"{channel_id}_{thread_id}_{message_id}_{guid}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=blob_name)

        self.logger.info(f"{LOG_PREFIX} Enqueueing message for channel '{channel_id}', thread '{thread_id}' with GUID '{guid}'.")

        try:
            blob_client.upload_blob(message, overwrite=True)
            self.logger.info(f"{LOG_PREFIX} Message successfully enqueued with ID '{blob_name}'.")
        except ResourceExistsError:
            self.logger.warning(f"{LOG_PREFIX} Message with GUID '{guid}' already exists.")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to enqueue the message with GUID '{guid}': {str(e)}")


    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, guid: str) -> None:
        """
        Removes a message from the queue based on channel_id, thread_id, message_id, and guid.
        """
        blob_name = f"{channel_id}_{thread_id}_{message_id}_{guid}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=blob_name)

        self.logger.info(f"{LOG_PREFIX} Dequeueing message '{blob_name}' for channel '{channel_id}', thread '{thread_id}' with GUID '{guid}'.")

        try:
            blob_client.delete_blob()
            self.logger.info(f"{LOG_PREFIX} Message '{blob_name}' successfully removed.")
        except ResourceNotFoundError:
            self.logger.warning(f"{LOG_PREFIX} Message '{blob_name}' not found.")
        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to dequeue message '{blob_name}': {str(e)}")


    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next message in the queue for a given channel/thread after the current_message_id.
        """
        self.logger.info(f"{LOG_PREFIX} Retrieving next message for channel '{channel_id}', thread '{thread_id}' after '{current_message_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs by channel_id and thread_id
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            if not filtered_blobs:
                return None, None

            current_timestamp = float(current_message_id)

            # Filter valid blobs with a message_id and sort them by timestamp
            filtered_blobs = [blob for blob in filtered_blobs if self.extract_message_id(blob.name) is not None]
            filtered_blobs.sort(key=lambda blob: self.extract_message_id(blob.name))

            # Find the next message after current_message_id
            next_blob = next((blob for blob in filtered_blobs if float(self.extract_message_id(blob.name)) > current_timestamp), None)

            if not next_blob:
                return None, None

            # Retrieve message content
            blob_client = self.blob_service_client.get_blob_client(data_container, next_blob.name)
            message_content = blob_client.download_blob().readall().decode('utf-8')
            next_message_id = next_blob.name.split('_')[-2]  # Extract message_id (ignores the GUID)

            return next_message_id, message_content

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to retrieve next message: {str(e)}")
            return None, None


    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are any older messages in the queue, excluding the current message.
        """
        self.logger.info(f"{LOG_PREFIX} Checking for older messages in queue for channel '{channel_id}', thread '{thread_id}', excluding message_id '{current_message_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs by channel_id and thread_id, excluding the current message
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            current_timestamp = float(current_message_id)

            # Filter blobs with a valid message_id
            filtered_blobs = [blob for blob in filtered_blobs if self.extract_message_id(blob.name) is not None]

            # Check if any message has an older timestamp than current_message_id
            has_older = any(float(self.extract_message_id(blob.name)) < current_timestamp for blob in filtered_blobs)

            return has_older

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to check older messages: {str(e)}")
            return False

    async def get_all_messages(self, data_container: str, channel_id: str, thread_id: str) -> List[str]:
        """
        Retrieves all messages for a given channel/thread.
        """
        self.logger.info(f"{LOG_PREFIX} Retrieving all messages for channel '{channel_id}', thread '{thread_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the given channel_id and thread_id
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            if not filtered_blobs:
                return []

            # Retrieve message contents
            messages_content = []
            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(data_container, blob.name)
                message_content = blob_client.download_blob().readall().decode('utf-8')
                messages_content.append(message_content)

            return messages_content

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to retrieve messages: {str(e)}")
            return []


    async def clear_all_queues(self) -> None:
        """
        Clears all messages from all Azure Blob Storage queues, regardless of TTL.
        """
        queue_containers = [
            self.messages_queue,
            self.internal_events_queue,
            self.external_events_queue,
            self.wait_queue,
        ]

        total_removed_files = 0  # Track the total number of removed blobs

        for queue_container in queue_containers:
            self.logger.info(f"{LOG_PREFIX} Clearing all messages in container: {queue_container}.")
            try:
                container_client = self.blob_service_client.get_container_client(queue_container)
                blobs = list(container_client.list_blobs())

                removed_files_count = 0  # Track removed blobs per container

                for blob in blobs:
                    blob_client = self.blob_service_client.get_blob_client(container=queue_container, blob=blob.name)
                    self.logger.debug(f"{LOG_PREFIX} Deleting blob: {blob.name}")
                    try:
                        blob_client.delete_blob()
                        self.logger.info(f"{LOG_PREFIX} Deleted message: {blob.name}")
                        removed_files_count += 1
                    except Exception as e:
                        self.logger.error(f"{LOG_PREFIX} Failed to delete message {blob.name}: {str(e)}")

                self.logger.info(f"{LOG_PREFIX} Removed {removed_files_count} messages from container '{queue_container}'.")
                total_removed_files += removed_files_count

            except Exception as e:
                self.logger.error(f"{LOG_PREFIX} Failed to clear container '{queue_container}': {str(e)}")

        self.logger.info(f"{LOG_PREFIX} Total removed messages across all containers: {total_removed_files}.")

    async def clean_all_queues(self) -> None:
        """
        Cleans up all expired messages across all Azure Blob Storage queues based on TTL values.
        """
        ttl_mapping = {
            self.messages_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL,
            self.internal_events_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL,
            self.external_events_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL,
            self.wait_queue: self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL,
        }

        total_removed_files = 0  # Track the total number of removed blobs

        for queue_container, ttl_seconds in ttl_mapping.items():
            self.logger.info(f"{LOG_PREFIX} Cleaning up expired messages in container: {queue_container} with TTL: {ttl_seconds} seconds.")
            try:
                container_client = self.blob_service_client.get_container_client(queue_container)
                blobs = list(container_client.list_blobs())

                removed_files_count = 0  # Track removed blobs per container

                for blob in blobs:
                    if self.is_message_expired(blob.name, ttl_seconds):
                        blob_client = self.blob_service_client.get_blob_client(container=queue_container, blob=blob.name)
                        self.logger.debug(f"{LOG_PREFIX} Deleting expired blob: {blob.name}")
                        try:
                            blob_client.delete_blob()
                            self.logger.info(f"{LOG_PREFIX} Deleted expired message: {blob.name}")
                            removed_files_count += 1
                        except Exception as e:
                            self.logger.error(f"{LOG_PREFIX} Failed to delete expired message {blob.name}: {str(e)}")

                self.logger.info(f"{LOG_PREFIX} Removed {removed_files_count} expired messages from container '{queue_container}'.")
                total_removed_files += removed_files_count

            except Exception as e:
                self.logger.error(f"{LOG_PREFIX} Failed to clean up expired messages from container '{queue_container}': {str(e)}")

        self.logger.info(f"{LOG_PREFIX} Total removed expired messages across all containers: {total_removed_files}.")

    async def clear_messages_queue(self, data_container: str, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the queue for a given channel and thread.
        """
        self.logger.info(f"{LOG_PREFIX} Clearing queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the given channel_id and thread_id
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(data_container, blob.name)
                blob_client.delete_blob()
                self.logger.info(f"{LOG_PREFIX} Message '{blob.name}' deleted successfully.")

        except Exception as e:
            self.logger.error(f"{LOG_PREFIX} Failed to clear queue: {str(e)}")

    async def create_container(self, data_container):
        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            if not container_client.exists():
                container_client.create_container()
                self.logger.info(f"Created container: {data_container}")
            else:
                self.logger.info(f"Container already exists: {data_container}")
        except Exception as e:
            self.logger.error(f"Failed to create container {data_container}: {str(e)}")
