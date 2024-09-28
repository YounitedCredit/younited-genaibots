import logging
import time
import traceback
from typing import List, Optional, Tuple

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from pydantic import BaseModel

from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager

AZURE_BLOB_STORAGE_QUEUE = "AZURE_BLOB_STORAGE_QUEUE"

class AzureBlobStorageConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING: str
    AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: str
    AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER: str

class AzureBlobStorageQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        self.logger = global_manager.logger

        super().__init__(global_manager)
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING[AZURE_BLOB_STORAGE_QUEUE]
        self.azure_blob_storage_config = AzureBlobStorageConfig(**config_dict)
        self.plugin_name = None

    def initialize(self):
        # Configure logging and initialize Azure Blob Service Client
        logging.getLogger("azure").setLevel(logging.WARNING)  # Set Azure SDK logging level to WARNING
        logging.getLogger("azure.storage.blob").setLevel(logging.WARNING)  # Set Azure Blob Storage logging level to WARNING

        self.logger.debug("Initializing Azure Blob Storage connection")
        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING,
                credential=credential
            )
            self.logger.info("Azure Blob Storage Backend: BlobServiceClient successfully created")
        except Exception as e:
            self.logger.error(f"Failed to create BlobServiceClient: {str(e)}")
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
    def internal_events_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER
    
    @property
    def external_events_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER
    
    @property
    def wait_queue(self):
        return self.azure_blob_storage_config.AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER

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
                    self.logger.info(f"Created container: {container}")
                else:
                    self.logger.info(f"Container already exists: {container}")
            except Exception as e:
                self.logger.error(f"Failed to create container {container}: {str(e)}")

    async def enqueue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str, message: str) -> None:
        blob_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=blob_name)

        try:
            self.logger.debug(f"Enqueuing message for channel '{channel_id}', thread '{thread_id}'.")
            blob_client.upload_blob(message, overwrite=True)
            self.logger.debug(f"Message successfully enqueued with ID '{message_id}' in blob '{blob_name}'.")
        except ResourceExistsError:
            self.logger.warning(f"Message with ID '{message_id}' already exists.")
        except Exception as e:
            self.logger.error(f"Failed to enqueue the message: {str(e)}")

    async def dequeue_message(self, data_container: str, channel_id: str, thread_id: str, message_id: str) -> None:
        blob_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=blob_name)

        self.logger.debug(f"Dequeueing message '{message_id}' from channel '{channel_id}', thread '{thread_id}'.")
        try:
            blob_client.delete_blob()
            self.logger.info(f"Message '{message_id}' successfully removed.")
        except ResourceNotFoundError:
            self.logger.warning(f"Message '{message_id}' not found.")
        except Exception as e:
            self.logger.error(f"Failed to dequeue message '{message_id}': {str(e)}")

    async def get_next_message(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info(f"Retrieving next message for channel '{channel_id}', thread '{thread_id}' after '{current_message_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            def extract_message_id(blob_name: str) -> float:
                parts = blob_name.split('_')
                return float(parts[2].replace('.txt', ''))

            current_timestamp = float(current_message_id)
            filtered_blobs.sort(key=lambda blob: extract_message_id(blob.name))

            next_blob = next((blob for blob in filtered_blobs if extract_message_id(blob.name) > current_timestamp), None)
            if not next_blob:
                return None, None

            blob_client = self.blob_service_client.get_blob_client(data_container, next_blob.name)
            message_content = blob_client.download_blob().readall().decode('utf-8')
            next_message_id = next_blob.name.split('_')[-1].replace('.txt', '')

            return next_message_id, message_content
        except Exception as e:
            self.logger.error(f"Failed to retrieve next message: {str(e)}")
            return None, None

    async def has_older_messages(self, data_container: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are any older messages in the Azure Blob storage, excluding the current message.
        """
        message_ttl = self.global_manager.bot_config.MESSAGE_QUEUING_TTL
        current_time = time.time()

        self.logger.info(f"Checking for older messages in channel '{channel_id}', thread '{thread_id}', excluding message_id '{current_message_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the given channel_id and thread_id
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            # Exclude the current message blob
            filtered_blobs = [blob for blob in filtered_blobs if current_message_id not in blob.name]

            # Log the filtered blobs for debugging purposes
            self.logger.debug(f"Filtered blobs excluding current message: {[blob.name for blob in filtered_blobs]}")

            for blob in filtered_blobs:
                message_id = blob.name.split('_')[-1].replace('.txt', '')
                timestamp = float(message_id)
                time_difference = current_time - timestamp

                # Remove the message if its time-to-live has expired
                if time_difference > message_ttl:
                    await self.dequeue_message(data_container, channel_id, thread_id, message_id)

            # Return whether there are any blobs left after filtering
            return len(filtered_blobs) > 0

        except Exception as e:
            self.logger.error(f"Failed to check for older messages: {str(e)}")
            return False


    async def get_all_messages(self, data_container: str, channel_id: str, thread_id: str) -> List[str]:
        self.logger.info(f"Retrieving all messages in queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
            messages_content = []

            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(data_container, blob.name)
                message_content = blob_client.download_blob().readall().decode('utf-8')
                messages_content.append(message_content)

            return messages_content
        except Exception as e:
            self.logger.error(f"Failed to retrieve all messages: {str(e)}")
            return []

    async def clear_messages_queue(self, data_container: str, channel_id: str, thread_id: str) -> None:
        self.logger.info(f"Clearing message queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            blobs = list(container_client.list_blobs())

            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(data_container, blob.name)
                blob_client.delete_blob()
        except Exception as e:
            self.logger.error(f"Failed to clear message queue: {str(e)}")
