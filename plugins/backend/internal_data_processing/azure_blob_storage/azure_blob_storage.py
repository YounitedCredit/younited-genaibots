import inspect
import json
import os
import traceback

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from pydantic import BaseModel

from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.backend.pricing_data import PricingData
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager

AZURE_BLOB_STORAGE = "AZURE_BLOB_STORAGE"

class AzureBlobStorageConfig(BaseModel):
    PLUGIN_NAME: str
    CONNECTION_STRING: str
    SESSIONS_CONTAINER: str
    MESSAGES_CONTAINER: str
    FEEDBACKS_CONTAINER: str
    CONCATENATE_CONTAINER: str
    PROMPTS_CONTAINER: str
    COSTS_CONTAINER: str
    PROCESSING_CONTAINER: str
    ABORT_CONTAINER: str
    VECTORS_CONTAINER: str

class AzureBlobStoragePlugin(InternalDataProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        self.logger =global_manager.logger
        super().__init__(global_manager)
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.plugin_configs = global_manager.config_manager.config_model.PLUGINS
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING[AZURE_BLOB_STORAGE]
        self.azure_blob_storage_config = AzureBlobStorageConfig(**config_dict)
        self.plugin_name = None

    def initialize(self):
        self.logger.debug("Initializing Azure Blob Storage connection")
        self.connection_string = self.azure_blob_storage_config.CONNECTION_STRING
        self.sessions_container = self.azure_blob_storage_config.SESSIONS_CONTAINER
        self.messages_container = self.azure_blob_storage_config.MESSAGES_CONTAINER
        self.feedbacks_container = self.azure_blob_storage_config.FEEDBACKS_CONTAINER
        self.concatenate_container = self.azure_blob_storage_config.CONCATENATE_CONTAINER
        self.prompts_container = self.azure_blob_storage_config.PROMPTS_CONTAINER
        self.costs_container = self.azure_blob_storage_config.COSTS_CONTAINER
        self.processing_container = self.azure_blob_storage_config.PROCESSING_CONTAINER
        self.abort_container = self.azure_blob_storage_config.ABORT_CONTAINER
        self.vectors_container = self.azure_blob_storage_config.VECTORS_CONTAINER
        self.plugin_name = self.azure_blob_storage_config.PLUGIN_NAME

        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=self.azure_blob_storage_config.CONNECTION_STRING, credential=credential)
            self.logger.debug("BlobServiceClient successfully created")
        except AzureError as e:
            self.initialization_failed = True
            self.logger.exception(f"Failed to create BlobServiceClient: {str(e)}")

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

    async def store_unmentioned_messages(self, channel_id, thread_id, message):
        try:
            self.logger.debug(f"Storing unmentioned messages for channel {channel_id}, thread {thread_id}")
            blob_name = f"unmentioned_messages_{channel_id}_{thread_id}.json"
            blob_name = blob_name.lower()
            blob_client = self.blob_service_client.get_blob_client(container=self.messages_container, blob=blob_name)
            if blob_client.exists():
                try:
                    existing_blob = blob_client.download_blob().readall()
                    messages = json.loads(existing_blob) if existing_blob else []
                    self.logger.debug("Existing messages successfully retrieved")
                except Exception as e:
                    self.logger.error(f"Failed to retrieve existing messages: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return
            else:
                self.logger.debug("No existing messages found, initializing empty list")
                messages = []

            messages.append(message)
            self.logger.debug(f"Appending new message: {message}")
            if blob_client.exists():
                try:
                    blob_client.upload_blob(json.dumps(messages), overwrite=True)
                    self.logger.info("Unmentioned messages stored successfully")
                except Exception as e:
                    self.logger.error(f"Failed to store unmentioned messages: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                try:
                    await self.write_data_content(data_container=self.messages_container, data_file=blob_name, data=json.dumps(messages))
                    self.logger.info("Unmentioned messages stored successfully")
                except Exception as e:
                    self.logger.error(f"Failed to store unmentioned messages: {str(e)}")
                    self.logger.error(traceback.format_exc())
        except Exception as e:
            self.logger.error(f"An error occurred while storing unmentioned messages: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def retrieve_unmentioned_messages(self, channel_id, thread_id):
        try:
            self.logger.debug(f"Retrieving unmentioned messages for channel {channel_id}, thread {thread_id}")
            blob_name = f"unmentioned_messages_{channel_id}_{thread_id}.json"
            blob_name = blob_name.lower()
            container_name = self.messages_container
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            if blob_client.exists():
                try:
                    blob_content = blob_client.download_blob().readall()
                    blob_client.delete_blob()  # Clear the blob after retrieving the content
                    messages = json.loads(blob_content)
                    self.logger.debug("Messages successfully retrieved and blob cleared")
                    return messages
                except Exception as e:
                    self.logger.error(f"Failed to retrieve or clear messages: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return []
            else:
                self.logger.debug("Failed to retrieve or clear messages, might be empty or first call")
                return []
        except Exception as e:
            self.logger.error(f"An error occurred while retrieving unmentioned messages: {str(e)}")
            self.logger.error(traceback.format_exc())
            return []

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
            blob_list = self.blob_service_client.get_container_client(container_name).list_blobs()
            file_names = []
            for blob in blob_list:
                base_name = os.path.basename(blob.name)
                file_name_without_extension = os.path.splitext(base_name)[0]
                file_names.append(file_name_without_extension)
            return file_names
        except AzureError as e:
            self.logger.error(f"An error occurred while listing blobs: {e}")
            return []

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

