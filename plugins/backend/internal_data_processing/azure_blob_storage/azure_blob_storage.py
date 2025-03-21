import json
import logging
import os
import traceback

from azure.core.exceptions import ResourceNotFoundError
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
    AZURE_BLOB_STORAGE_CHAINOFTHOUGHTS_CONTAINER: str


class AzureBlobStoragePlugin(InternalDataProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.logger = global_manager.logger
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("azure.storage.blob").setLevel(logging.WARNING)
        # If other libraries also cause verbose logs, you can set their log level too
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("azure.core.pipeline.policies").setLevel(logging.WARNING)

        self.global_manager = global_manager
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING[
            AZURE_BLOB_STORAGE]
        self.azure_blob_storage_config = AzureBlobStorageConfig(**config_dict)

        self.plugin_name = None
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

    @property
    def plugin_name(self):
        return "azure_blob_storage"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def sessions(self):
        return self.sessions_container

    @property
    def feedbacks(self):
        return self.feedbacks_container

    @property
    def concatenate(self):
        return self.concatenate_container

    @property
    def prompts(self):
        return self.prompts_container

    @property
    def costs(self):
        return self.costs_container

    @property
    def processing(self):
        return self.processing_container

    @property
    def abort(self):
        return self.abort_container

    @property
    def vectors(self):
        return self.vectors_container

    @property
    def custom_actions(self):
        return self.custom_actions_container

    @property
    def subprompts(self):
        return self.subprompts_container

    @property
    def chainofthoughts(self):
        return self.chainofthoughts_container

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
        self.chainofthoughts_container = self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CHAINOFTHOUGHTS_CONTAINER
        self.plugin_name = self.azure_blob_storage_config.PLUGIN_NAME

        try:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=self.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING,
                credential=credential
            )
            self.logger.info("Azure Blob Storage Backend: BlobServiceClient successfully created")
        except Exception as e:
            self.logger.error(f"Failed to create BlobServiceClient: {str(e)}")

        self.init_containers()

    def init_containers(self):
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
            self.subprompts_container
        ]

        for container in containers:
            try:
                container_client = self.blob_service_client.get_container_client(container)
                if not container_client.exists():
                    container_client.create_container()
                    self.logger.info(f"Created container: {container}")
                else:
                    self.logger.info(f"Container already exists: {container}")
            except Exception as e:
                self.logger.error(f"Failed to create container {container}: {str(e)}")

    async def append_data(self, container_name: str, data_identifier: str, data: str) -> None:
        self.logger.debug(f"Appending data to blob {data_identifier} in container {container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=data_identifier)
        try:
            blob_client.upload_blob(data, overwrite=True)
            self.logger.info(f"Data successfully appended to blob {data_identifier}")
        except Exception as e:
            self.logger.error(f"Failed to append data to blob: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def remove_data(self, container_name: str, datafile_name: str, data: str) -> None:
        self.logger.debug(f"Removing data from blob {datafile_name} in container {container_name}")
        try:
            data_lower = data.lower()
            existing_content = await self.read_data_content(container_name, datafile_name)
            if existing_content is None or existing_content == "":
                self.logger.info(f"Nothing to remove from blob {datafile_name}")
                return

            if data_lower in existing_content.lower():
                new_content = '\n'.join(
                    [line for line in existing_content.split('\n') if data_lower not in line.lower()])
                if new_content == "":
                    new_content = " "
                await self.write_data_content(container_name, datafile_name, new_content)
                self.logger.info(f"Data successfully removed from blob {datafile_name}")
        except Exception as e:
            self.logger.error(f"Failed to remove data from blob: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def read_data_content(self, data_container, data_file: str):
        self.logger.debug(f"Reading data content from {data_file} in {data_container}")
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=data_file)
        try:
            if blob_client.exists():
                download_stream = blob_client.download_blob()
                blob_data = download_stream.readall()
                self.logger.debug("Data successfully read")
                return blob_data.decode('utf-8')
            else:
                self.logger.warning(f"Blob not found: {data_file}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to read blob: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    async def write_data_content(self, data_container, data_file: str, data):
        self.logger.debug(f"Writing data content to {data_file} in {data_container}")
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=data_file)
        try:
            blob_client.upload_blob(data.encode('utf-8'), overwrite=True)
            self.logger.debug("Data successfully written to blob")
        except Exception as e:
            self.logger.error(f"Failed to write to blob: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def remove_data_content(self, data_container, data_file: str):
        self.logger.debug(f"Removing data content from {data_file} in {data_container}")
        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=data_file)
        try:
            blob_client.delete_blob()
            self.logger.debug("Blob successfully deleted")
        except ResourceNotFoundError:
            self.logger.warning(f"Blob not found: {data_file}")
        except Exception as e:
            self.logger.error(f"Failed to delete blob: {str(e)}")
            self.logger.error(traceback.format_exc())

    async def update_pricing(self, container_name, datafile_name: str, pricing_data):
        self.logger.debug(f"Updating pricing in blob {datafile_name} in container {container_name}")
        existing_content = await self.read_data_content(container_name, datafile_name)
        if existing_content:
            try:
                data = PricingData(**json.loads(existing_content))
                self.logger.debug("Existing pricing data retrieved")
            except Exception as e:
                self.logger.error(f"Failed to retrieve existing pricing data: {str(e)}")
                return
        else:
            self.logger.debug("No existing pricing data found, initializing new pricing structure")
            data = PricingData()

        data.total_tokens += pricing_data.total_tokens
        data.prompt_tokens += pricing_data.prompt_tokens
        data.completion_tokens += pricing_data.completion_tokens
        data.total_cost += pricing_data.total_cost
        data.input_cost += pricing_data.input_cost
        data.output_cost += pricing_data.output_cost
        self.logger.debug(f"Updated pricing data: {data.__dict__}")

        updated_content = json.dumps(data.__dict__)
        await self.write_data_content(container_name, datafile_name, updated_content)
        self.logger.debug("Pricing update completed")
        return data

    async def list_container_files(self, container_name: str):
        file_names = []
        container_client = self.blob_service_client.get_container_client(container_name)
        self.logger.debug(f"Listing files in container {container_name}")
        try:
            async for blob in container_client.list_blobs():
                file_names.append(os.path.basename(blob.name))
            return file_names
        except Exception as e:
            self.logger.error(f"Error listing files in container {container_name}: {e}")
            return []

    async def update_prompt_system_message(self, channel_id: str, thread_id: str, message: str):
        self.logger.debug(f"Updating prompt system message for channel {channel_id}, thread {thread_id}")
        blob_name = f"{channel_id}-{thread_id}.json"
        blob_client = self.blob_service_client.get_blob_client(container=self.sessions_container, blob=blob_name)

        try:
            # Download the session data
            download_stream = await blob_client.download_blob()
            blob_data = await download_stream.readall()
            session = json.loads(blob_data)
            self.logger.debug("Session blob content parsed into JSON")

            # Check if system message exists, if not add it at the beginning
            has_system = any(obj.get('role') == 'system' for obj in session)
            if not has_system:
                session.insert(0, {"role": "system", "content": message})
            else:
                for obj in session:
                    if obj.get('role') == 'system':
                        obj['content'] = message
                        break

            # Convert updated session to JSON and upload it back to the blob
            updated_session_data = json.dumps(session)
            await blob_client.upload_blob(updated_session_data, overwrite=True)
            self.logger.info("Prompt system message updated successfully")

        except Exception as e:
            self.logger.error(f"Failed to update prompt system message: {str(e)}")

    async def update_session(self, data_container: str, data_file: str, role: str, content: str):
        self.logger.debug(f"Updating session for file {data_file} in container {data_container}")

        blob_client = self.blob_service_client.get_blob_client(container=data_container, blob=data_file)

        try:
            # Try to read existing data from the blob
            if await blob_client.exists():
                self.logger.debug(f"Blob {data_file} exists, downloading content.")
                download_stream = await blob_client.download_blob()
                blob_data = await download_stream.readall()
                data = json.loads(blob_data)
                self.logger.debug("Blob content successfully parsed into JSON")
            else:
                self.logger.debug(f"Blob {data_file} not found, initializing new session data")
                data = []  # Initialize as an empty list if blob does not exist
        except ResourceNotFoundError:
            self.logger.debug(
                f"Blob {data_file} not found in container {data_container}, initializing new session data")
            data = []  # Initialize as an empty list if the blob does not exist
        except Exception as e:
            self.logger.error(f"Failed to read blob: {str(e)}")
            return

        # Append new role and content to the data
        data.append({"role": role, "content": content})
        self.logger.debug(f"Appended new role/content: {role}/{content}")

        try:
            # Upload the updated data back to the blob, overwriting the existing content
            updated_data = json.dumps(data)
            self.logger.debug(f"Uploading updated session data: {updated_data}")
            await blob_client.upload_blob(updated_data, overwrite=True)
            self.logger.debug(f"Session update completed for {data_file} in container {data_container}")
        except Exception as e:
            self.logger.error(f"Failed to write updated session to blob: {str(e)}")

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

    def create_container_sync(self, data_container):
        try:
            container_client = self.blob_service_client.get_container_client(data_container)
            if not container_client.exists():
                container_client.create_container()
                self.logger.info(f"Created container: {data_container}")
            else:
                self.logger.info(f"Container already exists: {data_container}")
        except Exception as e:
            self.logger.error(f"Failed to create container {data_container}: {str(e)}")

    async def file_exists(self, container_name: str, file_name: str) -> bool:
        """
        Check if a file (blob) exists in the specified container in Azure Blob Storage.

        Args:
            container_name (str): Name of the Azure Blob Storage container.
            file_name (str): Name of the file (blob) to check.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
            return await blob_client.exists()
        except Exception as e:
            self.logger.error(f"Error checking if file {file_name} exists in container {container_name}: {str(e)}")
            return False

    async def clear_container(self, container_name: str):
        """
        Clear all contents of the specified container in Azure Blob Storage.
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        try:
            async for blob in container_client.list_blobs():
                blob_client = container_client.get_blob_client(blob)
                blob_client.delete_blob()
                self.logger.info(f"Blob {blob.name} successfully deleted.")
            self.logger.info(f"All contents of container {container_name} have been cleared.")
        except Exception as e:
            self.logger.error(f"Failed to clear container {container_name}: {str(e)}")
            raise

    def clear_container_sync(self, container_name: str):
        """
        Clear all contents of the specified container in Azure Blob Storage.
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        try:
            for blob in container_client.list_blobs():
                blob_client = container_client.get_blob_client(blob)
                blob_client.delete_blob()
                self.logger.info(f"Blob {blob.name} successfully deleted.")
            self.logger.info(f"All contents of container {container_name} have been cleared.")
        except Exception as e:
            self.logger.error(f"Failed to clear container {container_name}: {str(e)}")
            raise
