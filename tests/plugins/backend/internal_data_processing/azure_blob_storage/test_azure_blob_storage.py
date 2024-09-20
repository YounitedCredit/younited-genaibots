import json
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


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_blob_storage",
        "AZURE_BLOB_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=account;AccountKey=key;EndpointSuffix=core.windows.net",
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
    plugin = AzureBlobStoragePlugin(global_manager=extended_mock_global_manager)
    try:
        plugin.initialize()
    except AzureError:
        pass
    return plugin

def test_initialize(azure_blob_storage_plugin):
    with patch.object(DefaultAzureCredential, '__init__', return_value=None):
        with patch.object(BlobServiceClient, '__init__', return_value=None):
            azure_blob_storage_plugin.initialize()
            assert azure_blob_storage_plugin.connection_string == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_CONNECTION_STRING
            assert azure_blob_storage_plugin.sessions_container == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_SESSIONS_CONTAINER
            assert azure_blob_storage_plugin.messages_container == azure_blob_storage_plugin.azure_blob_storage_config.AZURE_BLOB_STORAGE_MESSAGES_CONTAINER

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
        await azure_blob_storage_plugin.update_session('container', 'file', 'role', 'content')
        mock_read.assert_called_once_with('container', 'file')
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
async def test_store_unmentioned_messages_new_blob(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists.return_value = False
        mock_blob_client.upload_blob = AsyncMock()

        message = {"content": "test message"}
        await azure_blob_storage_plugin.store_unmentioned_messages("channel1", "thread1", message)

        mock_blob_client.upload_blob.assert_called_once()
        uploaded_content = mock_blob_client.upload_blob.call_args[0][0]
        assert json.loads(uploaded_content) == [message]

@pytest.mark.asyncio
async def test_retrieve_unmentioned_messages(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = MagicMock(return_value=True)

        mock_download_blob = MagicMock()
        mock_content = json.dumps([{"content": "test message"}]).encode()
        mock_download_blob.readall.return_value = mock_content
        mock_blob_client.download_blob.return_value = mock_download_blob

        mock_blob_client.delete_blob = MagicMock()

        messages = await azure_blob_storage_plugin.retrieve_unmentioned_messages("channel1", "thread1")

        assert messages == [{"content": "test message"}]
        mock_blob_client.delete_blob.assert_called_once()

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
async def test_store_unmentioned_messages_existing_blob(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = MagicMock(return_value=True)

        # Simuler le contenu existant du blob
        existing_content = json.dumps([{"content": "existing message"}]).encode('utf-8')
        mock_download_blob = MagicMock()
        mock_download_blob.readall = MagicMock(return_value=existing_content)
        mock_blob_client.download_blob = MagicMock(return_value=mock_download_blob)

        mock_blob_client.upload_blob = MagicMock()

        message = {"content": "new message"}
        await azure_blob_storage_plugin.store_unmentioned_messages("channel1", "thread1", message)

        # Vérifier que upload_blob a été appelé
        mock_blob_client.upload_blob.assert_called_once()

        # Vérifier le contenu uploadé
        uploaded_content = mock_blob_client.upload_blob.call_args[0][0]
        assert json.loads(uploaded_content) == [{"content": "existing message"}, {"content": "new message"}]


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
    assert azure_blob_storage_plugin.messages == azure_blob_storage_plugin.messages_container
    assert azure_blob_storage_plugin.feedbacks == azure_blob_storage_plugin.feedbacks_container
    assert azure_blob_storage_plugin.concatenate == azure_blob_storage_plugin.concatenate_container
    assert azure_blob_storage_plugin.prompts == azure_blob_storage_plugin.prompts_container
    assert azure_blob_storage_plugin.costs == azure_blob_storage_plugin.costs_container
    assert azure_blob_storage_plugin.processing == azure_blob_storage_plugin.processing_container
    assert azure_blob_storage_plugin.abort == azure_blob_storage_plugin.abort_container
    assert azure_blob_storage_plugin.vectors == azure_blob_storage_plugin.vectors_container

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

@pytest.mark.asyncio
async def test_store_unmentioned_messages_error_reading_blob(azure_blob_storage_plugin):
    with patch.object(BlobServiceClient, 'get_blob_client') as mock_get_blob_client:
        mock_blob_client = mock_get_blob_client.return_value
        mock_blob_client.exists = MagicMock(return_value=True)
        mock_blob_client.download_blob = MagicMock(side_effect=Exception("Read error"))
        mock_blob_client.upload_blob = MagicMock()

        message = {"content": "new message"}
        await azure_blob_storage_plugin.store_unmentioned_messages("channel1", "thread1", message)

        # Vérifier que upload_blob n'est pas appelé en cas d'erreur de lecture
        mock_blob_client.upload_blob.assert_not_called()
