import json
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from core.backend.pricing_data import PricingData
from plugins.backend.internal_data_processing.azure_blob_storage.azure_blob_storage import (
    AZURE_BLOB_STORAGE,
    AzureBlobStoragePlugin,
)


# Custom async iterator for list_blobs mock
class AsyncIterator:
    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_blob_storage",
        "AZURE_BLOB_STORAGE_CONNECTION_STRING": "https://fakeaccount.blob.core.windows.net/",
        "AZURE_BLOB_STORAGE_SESSIONS_CONTAINER": "sessions",
        "AZURE_BLOB_STORAGE_MESSAGES_CONTAINER": "messages",
        "AZURE_BLOB_STORAGE_FEEDBACKS_CONTAINER": "feedbacks",
        "AZURE_BLOB_STORAGE_CONCATENATE_CONTAINER": "concatenate",
        "AZURE_BLOB_STORAGE_PROMPTS_CONTAINER": "prompts",
        "AZURE_BLOB_STORAGE_COSTS_CONTAINER": "costs",
        "AZURE_BLOB_STORAGE_PROCESSING_CONTAINER": "processing",
        "AZURE_BLOB_STORAGE_ABORT_CONTAINER": "abort",
        "AZURE_BLOB_STORAGE_VECTORS_CONTAINER": "vectors",
        "AZURE_BLOB_STORAGE_CUSTOM_ACTIONS_CONTAINER": "custom_actions",
        "AZURE_BLOB_STORAGE_SUBPROMPTS_CONTAINER": "subprompts",
        "AZURE_BLOB_STORAGE_MESSAGES_QUEUE_CONTAINER": "messages_queue"
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING = {
        AZURE_BLOB_STORAGE: mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_blob_storage_plugin(extended_mock_global_manager):
    with patch.object(DefaultAzureCredential, '__init__', return_value=None), \
         patch.object(BlobServiceClient, '__init__', return_value=None):
        plugin = AzureBlobStoragePlugin(global_manager=extended_mock_global_manager)
        plugin.initialize()
        return plugin

def test_initialize(azure_blob_storage_plugin):
    with patch.object(DefaultAzureCredential, '__init__', return_value=None):
        with patch.object(BlobServiceClient, '__init__', return_value=None):
            azure_blob_storage_plugin.initialize()
            assert azure_blob_storage_plugin.connection_string == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING
            assert azure_blob_storage_plugin.sessions_container == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_SESSIONS_CONTAINER
            assert azure_blob_storage_plugin.messages_queue_container == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_MESSAGES_QUEUE_CONTAINER

def test_initialize_blob_service_client_error(mock_config, extended_mock_global_manager):
    with patch.object(BlobServiceClient, '__init__', side_effect=AzureError("Azure error")):
        plugin = AzureBlobStoragePlugin(global_manager=extended_mock_global_manager)
        plugin.initialize()
        assert plugin.initialization_failed is True  # Check if initialization failed

@pytest.mark.asyncio
async def test_update_session(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:
        mock_read.return_value = '[]'
        await azure_blob_storage_plugin.update_session('sessions', 'file', 'role', 'content')
        mock_read.assert_called_once_with('sessions', 'file')
        mock_write.assert_called_once()
        updated_content = mock_write.call_args[0][2]
        assert '{"role": "role", "content": "content"}' in updated_content

@pytest.mark.asyncio
async def test_read_data_content(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_blob_client.download_blob = AsyncMock()
        mock_download_blob = mock_blob_client.download_blob.return_value
        mock_download_blob.readall = AsyncMock(return_value=b'{"key": "value"}')

@pytest.mark.asyncio
async def test_read_data_content_blob_not_exists(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = MagicMock(return_value=False)
        mock_blob_client.download_blob = AsyncMock()  # Mock download_blob to ensure it's not called

        content = await azure_blob_storage_plugin.read_data_content('container', 'file')

        assert content is None
        mock_blob_client.download_blob.assert_not_called()

@pytest.mark.asyncio
async def test_remove_data_content(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_blob_client.delete_blob = AsyncMock()
        await azure_blob_storage_plugin.remove_data_content('container', 'file')
        mock_blob_client.delete_blob.assert_called_once()

@pytest.mark.asyncio
async def test_write_data_content(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.upload_blob = AsyncMock()
        await azure_blob_storage_plugin.write_data_content('container', 'file', 'data')
        mock_blob_client.upload_blob.assert_called_once_with(b'data', overwrite=True)



@pytest.mark.asyncio
async def test_update_pricing(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:

        existing_data = PricingData(total_tokens=100, prompt_tokens=50, completion_tokens=50, total_cost=1.0, input_cost=0.5, output_cost=0.5)
        mock_read.return_value = json.dumps(existing_data.__dict__)

        new_pricing_data = PricingData(total_tokens=50, prompt_tokens=25, completion_tokens=25, total_cost=0.5, input_cost=0.25, output_cost=0.25)

        updated_data = await azure_blob_storage_plugin.update_pricing("container", "datafile.json", new_pricing_data)

        assert updated_data.total_tokens == 150
        assert updated_data.prompt_tokens == 75
        assert updated_data.completion_tokens == 75
        assert updated_data.total_cost == 1.5
        assert updated_data.input_cost == 0.75
        assert updated_data.output_cost == 0.75

        mock_write.assert_called_once()

class AsyncIterator:
    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

@pytest.mark.asyncio
async def test_list_container_files(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_container_client') as mock_get_container_client:
        mock_container_client = mock_get_container_client.return_value
        mock_blob1 = MagicMock()
        mock_blob1.name = "path/to/file1.txt"
        mock_blob2 = MagicMock()
        mock_blob2.name = "another/path/file2.json"
        mock_container_client.list_blobs = MagicMock(return_value=AsyncIterator([mock_blob1, mock_blob2]))

        files = await azure_blob_storage_plugin.list_container_files("test_container")

        assert files == ["file1.txt", "file2.json"]
        mock_get_container_client.assert_called_once_with("test_container")

@pytest.mark.asyncio
async def test_update_prompt_system_message(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:

        mock_read.return_value = json.dumps([
            {"role": "system", "content": "old message"},
            {"role": "user", "content": "user message"}
        ])

        await azure_blob_storage_plugin.update_prompt_system_message("channel1", "thread1", "new system message")

        mock_write.assert_called_once()
        updated_content = json.loads(mock_write.call_args[0][2])
        assert updated_content[0]["role"] == "system"
        assert updated_content[0]["content"] == "new system message"

@pytest.mark.asyncio
async def test_update_session_invalid_json(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:

        # Simuler un contenu JSON invalide
        mock_read.return_value = 'invalid json'

        # Appel de la méthode avec des données invalides
        await azure_blob_storage_plugin.update_session('container', 'file', 'role', 'content')

        # Vérifier que write_data_content n'est pas appelé en cas de JSON invalide
        mock_write.assert_not_called()


@pytest.mark.asyncio
async def test_update_pricing_empty_initial_data(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:

        mock_read.return_value = None

        new_pricing_data = PricingData(total_tokens=50, prompt_tokens=25, completion_tokens=25, total_cost=0.5, input_cost=0.25, output_cost=0.25)

        updated_data = await azure_blob_storage_plugin.update_pricing("container", "datafile.json", new_pricing_data)

        assert updated_data.total_tokens == 50
        assert updated_data.prompt_tokens == 25
        assert updated_data.completion_tokens == 25
        assert updated_data.total_cost == 0.5
        assert updated_data.input_cost == 0.25
        assert updated_data.output_cost == 0.25

        mock_write.assert_called_once()

@pytest.mark.asyncio
async def test_not_implemented_methods(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.validate_request(None)

    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.handle_request(None)

    with pytest.raises(NotImplementedError):
        await azure_blob_storage_plugin.append_data(None, None, "some_data")

def test_properties(azure_blob_storage_plugin):
    assert azure_blob_storage_plugin.sessions == azure_blob_storage_plugin.sessions_container
    assert azure_blob_storage_plugin.feedbacks == azure_blob_storage_plugin.feedbacks_container
    assert azure_blob_storage_plugin.concatenate == azure_blob_storage_plugin.concatenate_container
    assert azure_blob_storage_plugin.prompts == azure_blob_storage_plugin.prompts_container
    assert azure_blob_storage_plugin.costs == azure_blob_storage_plugin.costs_container
    assert azure_blob_storage_plugin.processing == azure_blob_storage_plugin.processing_container
    assert azure_blob_storage_plugin.abort == azure_blob_storage_plugin.abort_container
    assert azure_blob_storage_plugin.vectors == azure_blob_storage_plugin.vectors_container
    assert azure_blob_storage_plugin.messages_queue == azure_blob_storage_plugin.messages_queue_container


@pytest.mark.asyncio
async def test_read_data_content_error(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_blob_client.download_blob = AsyncMock(side_effect=Exception("Read error"))

        content = await azure_blob_storage_plugin.read_data_content('container', 'file')
        assert content is None

@pytest.mark.asyncio
async def test_append_data_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        await azure_blob_storage_plugin.append_data('container', 'identifier', 'data')

def test_validate_request_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.validate_request('request')

def test_handle_request_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.handle_request('request')

@pytest.mark.asyncio
async def test_update_prompt_system_message_no_system_role(azure_blob_storage_plugin):
    with patch.object(azure_blob_storage_plugin, 'read_data_content', new_callable=AsyncMock) as mock_read, \
         patch.object(azure_blob_storage_plugin, 'write_data_content', new_callable=AsyncMock) as mock_write:

        mock_read.return_value = json.dumps([
            {"role": "user", "content": "user message"}
        ])

        await azure_blob_storage_plugin.update_prompt_system_message("channel1", "thread1", "new system message")

        mock_write.assert_not_called()

@pytest.mark.asyncio
async def test_list_container_files_error(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_container_client') as mock_get_container_client:
        mock_container_client = mock_get_container_client.return_value
        mock_container_client.list_blobs = MagicMock(side_effect=Exception("List error"))

        with pytest.raises(Exception, match="List error"):
            await azure_blob_storage_plugin.list_container_files("test_container")

def test_validate_request_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.validate_request('some_request')

def test_handle_request_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        azure_blob_storage_plugin.handle_request('some_request')

@pytest.mark.asyncio
async def test_append_data_not_implemented(azure_blob_storage_plugin):
    with pytest.raises(NotImplementedError):
        await azure_blob_storage_plugin.append_data('container', 'identifier', 'some_data')

@pytest.mark.asyncio
async def test_enqueue_message(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client', new_callable=MagicMock) as mock_blob_client:
        mock_blob = mock_blob_client.return_value
        mock_blob.upload_blob = AsyncMock()

        await azure_blob_storage_plugin.enqueue_message('channel1', 'thread1', 'message1', 'test_message')

        mock_blob.upload_blob.assert_called_once_with('test_message', overwrite=True)

@pytest.mark.asyncio
async def test_dequeue_message(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client', new_callable=MagicMock) as mock_blob_client:
        mock_blob = mock_blob_client.return_value
        mock_blob.delete_blob = AsyncMock()

        await azure_blob_storage_plugin.dequeue_message('channel1', 'thread1', 'message1')

        mock_blob.delete_blob.assert_called_once()

async def get_next_message(self, channel_id: str, thread_id: str, current_message_id: str) -> Tuple[Optional[str], Optional[str]]:
    self.logger.info(f"Checking for the next message in the queue for channel '{channel_id}', thread '{thread_id}' after message ID '{current_message_id}'.")

    try:
        container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
        blobs = list(container_client.list_blobs())

        filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
        self.logger.info(f"Found {len(filtered_blobs)} messages for channel '{channel_id}', thread '{thread_id}'.")

        if not filtered_blobs:
            self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
            return None, None

        # Mise à jour de l'expression régulière
        timestamp_regex = re.compile(rf"{channel_id}_{thread_id}_(\d+)\.txt")

        def extract_message_id(blob_name: str) -> int:
            match = timestamp_regex.search(blob_name)
            if match:
                return int(match.group(1))
            else:
                raise ValueError(f"Blob name '{blob_name}' does not match the expected format '{channel_id}_{thread_id}_<message_id>.txt'")

        current_id = int(current_message_id)

        filtered_blobs.sort(key=lambda blob: extract_message_id(blob.name))

        next_blob = next((blob for blob in filtered_blobs if extract_message_id(blob.name) > current_id), None)

        if not next_blob:
            self.logger.info(f"No newer message found after message ID '{current_message_id}' for channel '{channel_id}', thread '{thread_id}'.")
            return None, None

        blob_client = self.blob_service_client.get_blob_client(container=self.messages_queue_container, blob=next_blob.name)
        message_content = blob_client.download_blob().readall().decode('utf-8')

        next_message_id = str(extract_message_id(next_blob.name))

        self.logger.info(f"Next message retrieved: '{next_blob.name}' with ID '{next_message_id}'.")
        return next_message_id, message_content

    except ValueError as ve:
        self.logger.error(f"ValueError during message retrieval: {ve}")
        raise

    except Exception as e:
        self.logger.error(f"Failed to retrieve the next message for channel '{channel_id}', thread '{thread_id}': {str(e)}")
        return None, None

async def get_all_messages(self, channel_id: str, thread_id: str) -> List[str]:
    self.logger.info(f"Retrieving all messages in the queue for channel '{channel_id}', thread '{thread_id}'.")

    try:
        container_client = self.blob_service_client.get_container_client(self.messages_queue_container)
        blobs = list(container_client.list_blobs())

        filtered_blobs = [blob for blob in blobs if blob.name.startswith(f"{channel_id}_{thread_id}_")]
        self.logger.info(f"Found {len(filtered_blobs)} messages for channel '{channel_id}', thread '{thread_id}'.")

        if not filtered_blobs:
            self.logger.info(f"No messages found for channel '{channel_id}', thread '{thread_id}'.")
            return []

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

@pytest.mark.asyncio
async def test_clear_messages_queue(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_container_client', new_callable=MagicMock) as mock_container_client:
        mock_container = mock_container_client.return_value
        mock_blob1 = MagicMock()
        mock_blob1.name = "channel1_thread1_1001.txt"
        mock_blob2 = MagicMock()
        mock_blob2.name = "channel1_thread1_1002.txt"
        mock_container.list_blobs = MagicMock(return_value=[mock_blob1, mock_blob2])

        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob = AsyncMock()

        with patch.object(BlobServiceClient, 'get_blob_client', return_value=mock_blob_client):
            await azure_blob_storage_plugin.clear_messages_queue('channel1', 'thread1')

            assert mock_blob_client.delete_blob.call_count == 2
