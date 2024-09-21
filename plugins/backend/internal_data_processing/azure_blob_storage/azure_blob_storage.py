import inspect
import json
import os
import traceback
from typing import List
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from pydantic import BaseModel

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.backend.pricing_data import PricingData
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager
from typing import Optional, Tuple


AZURE_BLOB_STORAGE = "AZURE_BLOB_STORAGE"

class AzureBlobStorageConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_BLOB_STORAGE_CONNECTION_STRING: str
    AZURE_BLOB_STORAGE_SESSIONS_CONTAINER: str
    AZURE_BLOB_STORAGE_FEEDBACKS_CONTAINER: str
    AZURE_BLOB_STORAGE_CONCATENATE_CONTAINER: str
    AZURE_BLOB_STORAGE_PROMPTS_CONTAINER: str
    AZURE_BLOB_STORAGE_COSTS_CONTAINER: str
    AZURE_BLOB_STORAGE_PROCESSING_CONTAINER: str
    AZURE_BLOB_STORAGE_ABORT_CONTAINER: str
    AZURE_BLOB_STORAGE_VECTORS_CONTAINER: str
    AZURE_BLOB_STORAGE_CUSTOM_ACTIONS_CONTAINER: str
    AZURE_BLOB_STORAGE_SUBPROMPTS_CONTAINER: str
    AZURE_BLOB_STORAGE_MESSAGES_QUEUE_CONTAINER: str


class AzureBlobStoragePlugin(InternalDataProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        self.logger =global_manager.logger
        super().__init__(global_manager)
        self.initialization_failed = False
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.plugin_configs = global_manager.config_manager.config_model.PLUGINS
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING[AZURE_BLOB_STORAGE]
        self.azure_blob_storage_config = AzureBlobStorageConfig(**config_dict)
        self.plugin_name = None

    def initialize(self):
        self.logger.debug("Initializing Azure Blob Storage connection")
        self.connection_string = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING
        self.sessions_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_SESSIONS_CONTAINER
        self.feedbacks_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_FEEDBACKS_CONTAINER
        self.concatenate_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONCATENATE_CONTAINER
        self.prompts_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_PROMPTS_CONTAINER
        self.costs_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_COSTS_CONTAINER
        self.processing_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_PROCESSING_CONTAINER
        self.abort_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_ABORT_CONTAINER
        self.vectors_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_VECTORS_CONTAINER
        self.custom_actions_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CUSTOM_ACTIONS_CONTAINER
        self.subprompts_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_SUBPROMPTS_CONTAINER
        self.messages_queue_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_MESSAGES_QUEUE_CONTAINER
        self.plugin_name = self.azure_blob_storage_config.PLUGIN_NAME

        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING, credential=credential)
            self.logger.debug("BlobServiceClient successfully created")
        except Exception as e:
            self.initialization_failed = True
            self.logger.error(f"Failed to create BlobServiceClient: {str(e)}")

    @property
    def plugin_name(self):
        return "azure_blob_storage"

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
        # Implement the blob_messages_queue property
        return self.messages_queue_container
    
    def validate_request(self, request):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    def handle_request(self, request):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def append_data(self, container_name: str, data_identifier: str, data: str) -> None:
        # Implementation for appending data to Azure Blob Storage
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def update_session(self, data_container, data_file, role, content):
        self.logger.debug(f"Updating session for file {data_file} in container {data_container}")

        try:
            current_content = await self.read_data_content(data_container, data_file)

            if current_content is None:
                current_content = '[]'  # Default to an empty list as a JSON string

            try:
                data = json.loads(current_content) if current_content else []
                self.logger.debug("JSON content successfully parsed")
            except json.JSONDecodeError:
                self.logger.error("Failed to decode JSON, aborting update")
                return

            data.append({"role": role, "content": content})
            self.logger.debug(f"Appended new role/content: {role}/{content}")

            new_content = json.dumps(data)
            self.logger.debug("Data converted back to JSON")

            await self.write_data_content(data_container, data_file, new_content)
            self.logger.debug("Session update completed")
        except Exception as e:
            self.logger.error(f"An error occurred while updating the session: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def read_data_content(self, data_container, data_file : str):
        try:
            data_file = data_file.lower()
            self.logger.info(f"Reading data content from {data_file} in {data_container}")
            blob_client = self.blob_service_client.get_blob_client(data_container, data_file)
            if blob_client.exists():
                try:
                    download_stream = blob_client.download_blob()
                    blob_data = download_stream.readall()
                    self.logger.debug("Blob data successfully read")
                    return blob_data.decode('utf-8')
                except Exception as e:
                    self.logger.error(f"Failed to read blob: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return None
            else:
                self.logger.warning(f"Blob not found: {data_file}")
                return None
        except Exception as e:
            self.logger.error(f"An error occurred while reading the data content: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def remove_data_content(self, data_container, data_file: str):
        try:
            data_file = data_file.lower()
            self.logger.info(f"Removing data content from {data_file} in {data_container}")
            blob_client = self.blob_service_client.get_blob_client(data_container, data_file)
            if blob_client.exists():
                try:
                    blob_client.delete_blob()
                    self.logger.debug("Blob successfully deleted")
                except Exception as e:
                    self.logger.error(f"Failed to delete blob: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return None
            else:
                self.logger.debug(f"Blob not found: {data_file}")
                return None
        except Exception as e:
            self.logger.error(f"An error occurred while removing the data content: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def write_data_content(self, data_container, data_file: str, data):
        try:
            data_file = data_file.lower()
            self.logger.debug(f"Writing data content to {data_file} in {data_container}")
            blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=data_file)
            try:
                data = data.encode('utf-8')
                blob_client.upload_blob(data, overwrite=True)
                self.logger.debug("Data successfully written to blob")
            except Exception as e:
                self.logger.error(f"Failed to write data to blob: {str(e)}")
                self.logger.error(traceback.format_exc())
                return None
        except Exception as e:
            self.logger.error(f"An error occurred while writing the data content: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def update_pricing(self, container_name, datafile_name: str, pricing_data):
        try:
            datafile_name = datafile_name.lower()
            self.logger.debug(f"Updating pricing in blob {datafile_name} in container {container_name}")
            existing_content = await self.read_data_content(container_name, datafile_name)
            if existing_content:
                try:
                    data = PricingData(**json.loads(existing_content))
                    self.logger.debug("Existing pricing data retrieved")
                except Exception as e:
                    self.logger.error(f"Failed to retrieve existing pricing data: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return
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

            # Convert updated data to JSON
            updated_content = json.dumps(data.__dict__)
            # Write updated content to blob
            try:
                await self.write_data_content(container_name, datafile_name, updated_content)
                self.logger.debug("Pricing update completed")
            except Exception as e:
                self.logger.error(f"Failed to update pricing data: {str(e)}")
                self.logger.error(traceback.format_exc())
                return

            return data
        except Exception as e:
            self.logger.error(f"An error occurred while updating pricing: {str(e)}")
            self.logger.error(traceback.format_exc())
            return

    async def list_container_files(self, container_name: str):
        try:
            file_names = []
            blob_client = self.blob_service_client.get_container_client(container_name)
            async for blob in blob_client.list_blobs():
                file_names.append(os.path.basename(blob.name))
            return file_names
        except Exception as e:
            self.logger.error(f"Error listing files in container {container_name}: {e}")
            raise

    async def update_prompt_system_message(self, channel_id, thread_id, message):
        try:
            self.logger.debug(f"Updating prompt system message for channel {channel_id}, thread {thread_id}")
            blob_name = f"{channel_id}-{thread_id}.txt"
            blob_name = blob_name.lower()
            session = await self.read_data_content(self.sessions, blob_name)

            if session is None:
                self.logger.error(f"Session data not found for blob {blob_name}")
                return

            try:
                session_json = json.loads(session)
                self.logger.debug("Session string parsed into JSON")
            except json.JSONDecodeError:
                self.logger.error("Failed to decode session JSON")
                return

            updated = False
            for obj in session_json:
                if obj.get('role') == 'system':
                    self.logger.info("Found system role, updating content")
                    obj['content'] = message
                    updated = True
                    break

            if not updated:
                self.logger.warning("System role not found in session JSON")
                return

            updated_session = json.dumps(session_json)
            try:
                await self.write_data_content(self.sessions_container, blob_name, updated_session)
                self.logger.info("Prompt system message update completed successfully")
            except Exception as e:
                self.logger.error(f"Failed to update prompt system message: {str(e)}")
                self.logger.error(traceback.format_exc())
                return
        except Exception as e:
            self.logger.error(f"An error occurred while updating prompt system message: {str(e)}")
            self.logger.error(traceback.format_exc())
            return
        
    async def enqueue_message(self, channel_id: str, thread_id: str, message_id: str, message: str) -> None:
        """
        Adds a message to the Azure Blob Storage queue.
        The blob is named using `channel_id`, `thread_id`, and a unique message_id.
        """
        blob_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=blob_name)

        try:
            # Log that we are attempting to add a message
            self.logger.info(f"Attempting to enqueue message for channel '{channel_id}', thread '{thread_id}'.")

            # Upload the message to the blob
            blob_client.upload_blob(message, overwrite=True)
            self.logger.info(f"Message successfully enqueued with ID '{message_id}' in blob '{blob_name}'.")
        except ResourceExistsError:
            self.logger.warning(f"Message with ID '{message_id}' already exists in the queue.")
        except Exception as e:
            self.logger.error(f"Failed to enqueue the message for channel '{channel_id}', thread '{thread_id}': {str(e)}")

    async def dequeue_message(self, channel_id: str, thread_id: str, message_id: str) -> None:
        """
        Removes a message from the Azure Blob Storage queue after it has been processed.
        """
        blob_name = f"{channel_id}_{thread_id}_{message_id}.txt"
        blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=blob_name)

        self.logger.info(f"Attempting to dequeue message '{message_id}' from channel '{channel_id}', thread '{thread_id}'.")

        try:
            blob_client.delete_blob()
            self.logger.info(f"Message '{message_id}' successfully removed from the queue.")
        except ResourceNotFoundError:
            self.logger.warning(f"Message '{message_id}' not found in the queue.")
        except Exception as e:
            self.logger.error(f"Failed to dequeue message '{message_id}': {str(e)}")

    async def get_next_message(self, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the next (oldest) message for a `channel_id`, `thread_id` after `current_message_id`.
        Returns a tuple (next_message_id, message_content). If no message is found, returns (None, None).
        """
        self.logger.info(f"Checking for the next message in the queue for channel '{channel_id}', thread '{thread_id}' after message ID '{current_message_id}'.")

        try:
            # Get all blobs in the message queue container
            container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the specific `channel_id` and `thread_id`
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
            self.logger.info(f"Found {len(filtered_blobs)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_blobs:
                self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
                return None, None

            # Regular expression to match the blob name structure: {channel_id}_{thread_id}_{message_id}.txt
            timestamp_regex = re.compile(rf"{channel_id}_(\d+\.\d+)_(\d+\.\d+)\.txt")

            # Extract the message_id (timestamp) from the blob name using regex
            def extract_message_id(blob_name: str) -> float:
                match = timestamp_regex.search(blob_name)
                if match:
                    return float(match.group(2))  # Group 2 contains the message_id
                else:
                    raise ValueError(f"Blob name '{blob_name}' does not match the expected format '{channel_id}_{thread_id}_<message_id>.txt'")

            # Get the timestamp of the current message
            current_timestamp = extract_message_id(f"{channel_id}_{thread_id}_{current_message_id}.txt")

            # Sort blobs by the message_id
            filtered_blobs.sort(key=lambda blob: extract_message_id(blob.name))

            # Find the next message based on the timestamp comparison
            next_blob = next((blob for blob in filtered_blobs if extract_message_id(blob.name) > current_timestamp), None)

            if not next_blob:
                self.logger.info(f"No newer message found after message ID '{current_message_id}' for channel '{channel_id}', thread '{thread_id}'.")
                return None, None

            # Read the content of the next message
            blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=next_blob.name)
            message_content = blob_client.download_blob().readall().decode('utf-8')

            next_message_id = next_blob.name.split('_')[-1].replace('.txt', '')

            self.logger.info(f"Next message retrieved: '{next_blob.name}' with ID '{next_message_id}'.")
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
        Retrieves the contents of all messages for a `channel_id` and `thread_id` from the Azure Blob Storage queue.
        Returns a list of message contents.
        """
        self.logger.info(f"Retrieving all messages in the queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            # Get all blobs in the message queue container
            container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the specific `channel_id` and `thread_id`
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
            self.logger.info(f"Found {len(filtered_blobs)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_blobs:
                self.logger.info(f"No messages found for channel '{channel_id}', thread '{thread_id}'.")
                return []

            # Read the content of each filtered message blob
            messages_content = []
            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=blob.name)
                message_content = blob_client.download_blob().readall().decode('utf-8')
                messages_content.append(message_content)

            self.logger.info(f"Retrieved {len(messages_content)} messages for channel '{channel_id}', thread '{thread_id}'.")
            return messages_content

        except Exception as e:
            self.logger.error(f"Failed to retrieve all messages for channel '{channel_id}', thread '{thread_id}': {str(e)}")
            return []

    async def has_older_messages(self, channel_id: str, thread_id: str) -> bool:
        """
        Checks if there are any older messages in the Azure Blob Storage queue for a given channel and thread.
        """
        message_ttl = self.global_manager.bot_config.MESSAGE_QUEUING_TTL
        current_time = int(time.time())

        self.logger.info(f"Checking for older messages in channel '{channel_id}', thread '{thread_id}'.")

        try:
            # Get all blobs in the message queue container
            container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the specific `channel_id` and `thread_id`
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
            self.logger.info(f"Found {len(filtered_blobs)} messages for channel '{channel_id}', thread '{thread_id}'.")

            if not filtered_blobs:
                self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
                return False

            updated_files = []
            for blob in filtered_blobs:
                # Extract the message_id (timestamp) from the blob name
                message_id = blob.name.split('_')[-1].split('.')[0]
                timestamp = float(message_id)

                if current_time - timestamp > message_ttl:
                    self.logger.warning(f"Removing message '{blob.name}' as it is older than {message_ttl} seconds.")
                    await self.dequeue_message(channel_id, thread_id, message_id)
                else:
                    updated_files.append(blob.name)

            # Return True if there are valid messages left after removing old ones
            return len(updated_files) > 0

        except Exception as e:
            self.logger.error(f"Failed to check for older messages: {str(e)}")
            return False

    async def clear_messages_queue(self, channel_id: str, thread_id: str) -> None:
        """
        Clears all messages in the Azure Blob Storage queue for a given channel and thread.
        """
        self.logger.info(f"Clearing messages queue for channel '{channel_id}', thread '{thread_id}'.")

        try:
            # Get all blobs in the message queue container
            container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
            blobs = list(container_client.list_blobs())

            # Filter blobs for the specific `channel_id` and `thread_id`
            filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]

            for blob in filtered_blobs:
                blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=blob.name)
                blob_client.delete_blob()
                self.logger.info(f"Message '{blob.name}' successfully deleted from the queue.")

        except Exception as e:
            self.logger.error(f"Failed to clear messages queue for channel '{channel_id}', thread '{thread_id}': {str(e)}")
