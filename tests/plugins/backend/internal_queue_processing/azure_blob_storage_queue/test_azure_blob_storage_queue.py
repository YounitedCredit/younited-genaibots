from unittest.mock import MagicMock, create_autospec, patch
import pydantic
import pytest
from azure.storage.blob import BlobClient, ContainerClient

from core.global_manager import GlobalManager
from plugins.backend.internal_queue_processing.azure_blob_storage_queue.azure_blob_storage_queue import (
    AzureBlobStorageQueuePlugin,
)


@pytest.fixture
def mock_global_manager():
    # Créez un mock spécifique basé sur GlobalManager
    mock = create_autospec(GlobalManager, instance=True)

    # Configurez les attributs nécessaires
    mock.logger = MagicMock()

    # Configurer config_manager avec config_model
    mock.config_manager = MagicMock()
    mock.config_manager.config_model = MagicMock()
    mock.config_manager.config_model.PLUGINS = MagicMock()
    mock.config_manager.config_model.PLUGINS.BACKEND = MagicMock()
    mock.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {}

    # Configurer plugin_manager
    mock.plugin_manager = MagicMock()

    return mock

@pytest.fixture
def mock_azure_blob_storage_config():
    return {
        "PLUGIN_NAME": "azure_blob_storage_queue",
        "AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING": "https://fakeaccount.blob.core.windows.net",
        "AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER": "messages",
        "AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER": "internal_events",
        "AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER": "external_events",
        "AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER": "wait",
        "AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL": 3600,
        "AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL": 3600,
        "AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL": 3600,
        "AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL": 3600,
    }

@pytest.fixture
def azure_blob_storage_queue_plugin(mock_global_manager, mock_azure_blob_storage_config):
    with patch('azure.identity.DefaultAzureCredential') as mock_credential, \
         patch('plugins.backend.internal_queue_processing.azure_blob_storage_queue.azure_blob_storage_queue.BlobServiceClient.__init__', return_value=None) as mock_blob_service_init, \
         patch('plugins.backend.internal_queue_processing.azure_blob_storage_queue.azure_blob_storage_queue.BlobServiceClient') as mock_blob_service_client:

        # Configurer le BlobServiceClient mock
        mock_blob_service = MagicMock()
        mock_blob_service_client.return_value = mock_blob_service

        # Configurer get_container_client pour retourner un MagicMock
        mock_container_client = MagicMock(spec=ContainerClient)
        mock_blob_service.get_container_client.return_value = mock_container_client

        # Mock exists() pour retourner False (container n'existe pas)
        mock_container_client.exists.return_value = False

        # Mock create_container() pour simuler la création d'un container
        mock_container_client.create_container.return_value = None

        # Injecter la configuration mockée dans le config_manager
        mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
            "AZURE_BLOB_STORAGE_QUEUE": mock_azure_blob_storage_config
        }

        # Initialiser le plugin
        plugin = AzureBlobStorageQueuePlugin(mock_global_manager)
        plugin.initialize()

        return plugin

def test_initialize(azure_blob_storage_queue_plugin, mock_azure_blob_storage_config):
    # Le plugin a déjà été initialisé dans la fixture
    assert azure_blob_storage_queue_plugin.plugin_name == "azure_blob_storage_queue"

    # Vérifier que BlobServiceClient a été initialisé avec la chaîne de connexion
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_blob_service_client.get_container_client.assert_any_call(mock_azure_blob_storage_config["AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER"])
    mock_blob_service_client.get_container_client.assert_any_call(mock_azure_blob_storage_config["AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER"])
    mock_blob_service_client.get_container_client.assert_any_call(mock_azure_blob_storage_config["AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER"])
    mock_blob_service_client.get_container_client.assert_any_call(mock_azure_blob_storage_config["AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER"])

    # Vérifier que create_container a été appelé pour chaque container
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    assert mock_container_client.create_container.call_count == 4  # Quatre containers

@pytest.mark.asyncio
async def test_enqueue_message(azure_blob_storage_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    message = "Test Message"
    guid = "test_guid"

    # Récupérer le mock_blob_service_client de la fixture
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client

    # Configurer le mock_blob_client
    mock_blob_client = MagicMock(spec=BlobClient)
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client

    print("Enqueuing message...")
    await azure_blob_storage_queue_plugin.enqueue_message("messages", channel_id, thread_id, message_id, message, guid)
    print("Message enqueued.")

    # Vérifier que get_blob_client a été appelé correctement
    mock_blob_service_client.get_blob_client.assert_called_once_with(container="messages", blob=f"{channel_id}_{thread_id}_{message_id}_{guid}.txt")
    mock_blob_client.upload_blob.assert_called_once_with(message, overwrite=True)

@pytest.mark.asyncio
async def test_dequeue_message(azure_blob_storage_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    guid = "test_guid"

    # Récupérer le mock_blob_service_client de la fixture
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client

    # Configurer le mock_blob_client
    mock_blob_client = MagicMock(spec=BlobClient)
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client

    print("Dequeuing message...")
    await azure_blob_storage_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id, guid)
    print("Message dequeued.")

    # Vérifier que get_blob_client a été appelé correctement
    mock_blob_service_client.get_blob_client.assert_called_once_with(container="messages", blob=f"{channel_id}_{thread_id}_{message_id}_{guid}.txt")
    mock_blob_client.delete_blob.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup_expired_messages(azure_blob_storage_queue_plugin):
    channel_id = "channel_1"
    thread_id = "thread_1"
    expired_blob_name = f"{channel_id}_{thread_id}_1632492370.txt"  # Expired
    valid_blob_name = f"{channel_id}_{thread_id}_1632492374.txt"    # Not expired
    ttl_seconds = 3600

    # Récupérer le mock_blob_service_client de la fixture
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value

    # Configurer list_blobs avec des blobs ayant des noms spécifiques
    blob_expired = MagicMock()
    blob_expired.name = expired_blob_name
    blob_valid = MagicMock()
    blob_valid.name = valid_blob_name
    mock_container_client.list_blobs.return_value = [blob_expired, blob_valid]

    # Configurer get_blob_client pour chaque blob
    mock_blob_client_expired = MagicMock(spec=BlobClient)
    mock_blob_client_valid = MagicMock(spec=BlobClient)
    mock_blob_service_client.get_blob_client.side_effect = lambda container, blob: mock_blob_client_expired if blob == expired_blob_name else mock_blob_client_valid

    # Configurer is_message_expired pour retourner True pour expired_blob_name et False pour valid_blob_name
    def is_message_expired_side_effect(blob_name, ttl):
        return blob_name == expired_blob_name

    with patch.object(azure_blob_storage_queue_plugin, 'is_message_expired', side_effect=is_message_expired_side_effect):
        print("Cleaning up expired messages...")
        await azure_blob_storage_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)
        print("Expired messages cleaned up.")

    # Vérifier que delete_blob a été appelé une seule fois pour expired_blob_name
    mock_blob_client_expired.delete_blob.assert_called_once()
    mock_blob_client_valid.delete_blob.assert_not_called()


@pytest.mark.asyncio
async def test_get_next_message(azure_blob_storage_queue_plugin):
    channel_id = "channel1"
    thread_id = "thread1"
    current_message_id = "1632492373.1234"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"
    current_guid = "current-guid"
    next_guid = "next-guid"

    blob_list = [
        f"{channel_id}_{thread_id}_1632492371.0000_earlier-guid.txt",
        f"{channel_id}_{thread_id}_{current_message_id}_{current_guid}.txt",
        f"{channel_id}_{thread_id}_{next_message_id}_{next_guid}.txt"
    ]

    # Récupérer le mock_blob_service_client de la fixture
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value

    # Configurer list_blobs avec des blobs ayant des noms spécifiques
    blob_earlier = MagicMock()
    blob_earlier.name = blob_list[0]
    blob_current = MagicMock()
    blob_current.name = blob_list[1]
    blob_next = MagicMock()
    blob_next.name = blob_list[2]
    mock_container_client.list_blobs.return_value = [blob_earlier, blob_current, blob_next]

    # Configurer get_blob_client pour chaque blob
    mock_blob_client_earlier = MagicMock(spec=BlobClient)
    mock_blob_client_earlier.download_blob.return_value.readall.return_value = b"1632492371.0000"  # bytes

    mock_blob_client_current = MagicMock(spec=BlobClient)
    mock_blob_client_current.download_blob.return_value.readall.return_value = b"1632492373.1234"  # bytes

    mock_blob_client_next = MagicMock(spec=BlobClient)
    mock_blob_client_next.download_blob.return_value.readall.return_value = expected_content.encode('utf-8')  # bytes

    # Configurer get_blob_client side_effect pour retourner les mocks appropriés
    def get_blob_client_side_effect(container, blob):
        if blob == blob_next.name:
            return mock_blob_client_next
        elif blob == blob_current.name:
            return mock_blob_client_current
        elif blob == blob_earlier.name:
            return mock_blob_client_earlier
        else:
            return MagicMock(spec=BlobClient)  # Mock sans comportement spécifique

    mock_blob_service_client.get_blob_client.side_effect = get_blob_client_side_effect

    print("Getting next message...")
    result_message_id, result_content = await azure_blob_storage_queue_plugin.get_next_message(
        "messages", channel_id, thread_id, current_message_id
    )
    print("Next message retrieved.")

    # Vérifier les résultats
    assert result_message_id == next_message_id
    assert result_content == expected_content

    # Vérifier que get_blob_client a été appelé avec le bon blob
    mock_blob_service_client.get_blob_client.assert_called_once_with(
        "messages", f"{channel_id}_{thread_id}_{next_message_id}_{next_guid}.txt"
    )
    mock_blob_client_next.download_blob.assert_called_once()


@pytest.mark.asyncio
async def test_clear_all_queues(azure_blob_storage_queue_plugin):
    # Récupérer le mock_blob_service_client de la fixture
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client

    # Configurer list_blobs pour chaque container
    mock_blob_service_client.get_container_client.side_effect = [
        MagicMock(spec=ContainerClient, list_blobs=MagicMock(return_value=[MagicMock(name='blob1'), MagicMock(name='blob2')])),
        MagicMock(spec=ContainerClient, list_blobs=MagicMock(return_value=[MagicMock(name='blob3'), MagicMock(name='blob4')])),
        MagicMock(spec=ContainerClient, list_blobs=MagicMock(return_value=[MagicMock(name='blob5'), MagicMock(name='blob6')])),
        MagicMock(spec=ContainerClient, list_blobs=MagicMock(return_value=[MagicMock(name='blob7'), MagicMock(name='blob8')]))
    ]

    # Configurer get_blob_client pour retourner des mock_blob_clients distincts
    mock_blob_clients = [MagicMock(spec=BlobClient) for _ in range(8)]
    mock_blob_service_client.get_blob_client.side_effect = mock_blob_clients

    print("Clearing all queues...")
    await azure_blob_storage_queue_plugin.clear_all_queues()
    print("All queues cleared.")

    # Vérifier que get_blob_client a été appelé 8 fois
    assert mock_blob_service_client.get_blob_client.call_count == 8

    # Vérifier que delete_blob a été appelé 8 fois
    for mock_blob_client in mock_blob_service_client.get_blob_client.side_effect:
        mock_blob_client.delete_blob.assert_called_once()

from unittest.mock import MagicMock, create_autospec, patch
import pytest
from azure.storage.blob import BlobClient, ContainerClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import time

# Existing fixtures are reused from your current setup
# mock_global_manager, mock_azure_blob_storage_config, azure_blob_storage_queue_plugin


def test_initialize_failure(mock_global_manager, mock_azure_blob_storage_config):
    """
    Test that the initialize method handles exceptions during BlobServiceClient creation.
    """
    # Inject the proper config key to avoid KeyError
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
        "AZURE_BLOB_STORAGE_QUEUE": mock_azure_blob_storage_config
    }

    with patch('azure.identity.DefaultAzureCredential') as mock_credential, \
         patch('azure.storage.blob.BlobServiceClient.__init__', side_effect=Exception("Connection failed")):

        with pytest.raises(Exception, match="Connection failed"):
            plugin = AzureBlobStorageQueuePlugin(mock_global_manager)
            plugin.initialize()

def test_init_containers_existing(azure_blob_storage_queue_plugin, mock_azure_blob_storage_config):
    """
    Test init_containers when containers already exist (no creation needed).
    """
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client

    # Create separate mocks for each container
    mock_container_client_1 = MagicMock()
    mock_container_client_2 = MagicMock()
    mock_container_client_3 = MagicMock()
    mock_container_client_4 = MagicMock()

    # Mock exists() to return True for each container
    mock_container_client_1.exists.return_value = True
    mock_container_client_2.exists.return_value = True
    mock_container_client_3.exists.return_value = True
    mock_container_client_4.exists.return_value = True

    # Return the mocked container client for each call to get_container_client
    mock_blob_service_client.get_container_client.side_effect = [
        mock_container_client_1, 
        mock_container_client_2, 
        mock_container_client_3, 
        mock_container_client_4
    ]

    azure_blob_storage_queue_plugin.init_containers()

    # Ensure create_container is NOT called when containers exist
    mock_container_client_1.create_container.assert_not_called()
    mock_container_client_2.create_container.assert_not_called()
    mock_container_client_3.create_container.assert_not_called()
    mock_container_client_4.create_container.assert_not_called()


def test_extract_message_id_valid(azure_blob_storage_queue_plugin):
    """
    Test extract_message_id with a valid blob name that includes a UNIX timestamp and GUID.
    """
    # Correct blob name format with a UNIX timestamp and a GUID (without underscores in the timestamp section)
    valid_blob_name = "channel1_thread1_1632492370.1234_guid.txt"
    
    # Call the method and capture the result
    message_id = azure_blob_storage_queue_plugin.extract_message_id(valid_blob_name)
    
    # Ensure correct message ID extraction
    assert message_id == 1632492370.1234


def test_extract_message_id_invalid(azure_blob_storage_queue_plugin):
    """
    Test extract_message_id with invalid blob name.
    """
    invalid_blob_name = "invalid_blob_name.txt"
    message_id = azure_blob_storage_queue_plugin.extract_message_id(invalid_blob_name)
    assert message_id is None

def test_is_message_expired_true(azure_blob_storage_queue_plugin):
    """
    Test is_message_expired when the message has expired, using the correct blob name format.
    """
    # Correct blob name format with a UNIX timestamp and GUID
    blob_name = "channel1_thread1_1632492370.1234_guid.txt"  # Old timestamp
    
    ttl_seconds = 3600  # 1 hour (3600 seconds)
    
    # Simulate the current time being *more than 1 hour* after the message timestamp
    message_timestamp = 1632492370.1234
    current_time = message_timestamp + ttl_seconds + 100  # Simulate time 100 seconds after TTL
    
    # Patch time.time() to return the simulated current time
    with patch('time.time', return_value=current_time):
        expired = azure_blob_storage_queue_plugin.is_message_expired(blob_name, ttl_seconds)

        # Assert that the message has indeed expired
        assert expired is True

def test_is_message_expired_false(azure_blob_storage_queue_plugin):
    """
    Test is_message_expired when the message has not expired.
    """
    blob_name = "channel_1_thread_1_1632492370.txt"  # Current timestamp
    ttl_seconds = 3600  # 1 hour
    with patch('time.time', return_value=1632492371):  # Simulate current time + 1 second
        expired = azure_blob_storage_queue_plugin.is_message_expired(blob_name, ttl_seconds)
        assert expired is False


@pytest.mark.asyncio
async def test_cleanup_expired_messages_no_expiry(azure_blob_storage_queue_plugin):
    """
    Test cleanup_expired_messages when there are no expired messages.
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    valid_blob_name = f"{channel_id}_{thread_id}_1632492374.txt"  # Not expired
    ttl_seconds = 3600

    # Mock list_blobs to return blobs
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = [MagicMock(name=valid_blob_name)]

    # Mock is_message_expired to return False (no expiration)
    with patch.object(azure_blob_storage_queue_plugin, 'is_message_expired', return_value=False):
        await azure_blob_storage_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)

    # Ensure delete_blob is not called
    mock_blob_service_client.get_blob_client.return_value.delete_blob.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_expired_messages_with_expiry(azure_blob_storage_queue_plugin):
    """
    Test cleanup_expired_messages when messages are expired.
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    expired_blob_name = f"{channel_id}_{thread_id}_1632492370.txt"  # Expired
    ttl_seconds = 3600

    # Mock list_blobs to return blobs
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = [MagicMock(name=expired_blob_name)]

    # Mock is_message_expired to return True for expired blobs
    with patch.object(azure_blob_storage_queue_plugin, 'is_message_expired', return_value=True):
        await azure_blob_storage_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)

    # Ensure delete_blob is called for expired blobs
    mock_blob_service_client.get_blob_client.return_value.delete_blob.assert_called_once()


@pytest.mark.asyncio
async def test_dequeue_message_not_found(azure_blob_storage_queue_plugin):
    """
    Test dequeue_message when the message is not found (ResourceNotFoundError).
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    message_id = "1"
    guid = "test_guid"

    # Mock BlobClient
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_blob_client = mock_blob_service_client.get_blob_client.return_value

    # Simulate ResourceNotFoundError when trying to delete blob
    mock_blob_client.delete_blob.side_effect = ResourceNotFoundError

    await azure_blob_storage_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id, guid)

    # Ensure delete_blob is called, and it raised the appropriate exception
    mock_blob_client.delete_blob.assert_called_once()
    azure_blob_storage_queue_plugin.logger.warning.assert_called_with(f"[AZURE_BLOB_QUEUE] Message '{channel_id}_{thread_id}_{message_id}_{guid}.txt' not found.")


@pytest.mark.asyncio
async def test_enqueue_message_already_exists(azure_blob_storage_queue_plugin):
    """
    Test enqueue_message when the blob already exists (ResourceExistsError).
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    message_id = "1"
    message = "Test Message"
    guid = "test_guid"

    # Mock BlobClient
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_blob_client = mock_blob_service_client.get_blob_client.return_value

    # Simulate ResourceExistsError when trying to upload blob
    mock_blob_client.upload_blob.side_effect = ResourceExistsError

    await azure_blob_storage_queue_plugin.enqueue_message("messages", channel_id, thread_id, message_id, message, guid)

    # Ensure upload_blob is called, and a warning is logged for existing blob
    mock_blob_client.upload_blob.assert_called_once_with(message, overwrite=True)
    azure_blob_storage_queue_plugin.logger.warning.assert_called_with(f"[AZURE_BLOB_QUEUE] Message with GUID '{guid}' already exists.")

def test_initialize_with_missing_config(mock_global_manager):
    """
    Test that the initialize method handles missing configuration keys.
    """
    # Modify the config to be missing essential keys
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
        "AZURE_BLOB_STORAGE_QUEUE": {
            # Empty configuration dictionary
        }
    }

    with pytest.raises(pydantic.ValidationError) as exc_info:
        plugin = AzureBlobStorageQueuePlugin(mock_global_manager)

    # Ensure the error message mentions the missing fields
    assert "PLUGIN_NAME" in str(exc_info.value)
    assert "AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING" in str(exc_info.value)

def test_initialize_blob_connection_error(mock_global_manager, mock_azure_blob_storage_config):
    """
    Test that the initialize method handles exceptions during BlobServiceClient creation.
    """
    # Ensure the configuration is correctly set
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
        "AZURE_BLOB_STORAGE_QUEUE": mock_azure_blob_storage_config
    }

    # Simulate an error in BlobServiceClient initialization
    with patch('azure.storage.blob.BlobServiceClient.__init__', side_effect=Exception("Connection error")):
        plugin = AzureBlobStorageQueuePlugin(mock_global_manager)

        with pytest.raises(Exception, match="Connection error"):
            plugin.initialize()

    # Ensure the error is logged
    mock_global_manager.logger.error.assert_called_with("[AZURE_BLOB_QUEUE] Failed to create BlobServiceClient: Connection error")

def test_is_message_expired_with_invalid_timestamp(azure_blob_storage_queue_plugin):
    """
    Test is_message_expired when the blob name has an invalid timestamp format.
    """
    invalid_blob_name = "invalid_timestamp_blob.txt"
    ttl_seconds = 3600

    # Ensure it returns False due to invalid timestamp extraction
    expired = azure_blob_storage_queue_plugin.is_message_expired(invalid_blob_name, ttl_seconds)
    assert not expired

def test_is_message_expired_valid(azure_blob_storage_queue_plugin):
    """
    Test is_message_expired with a valid timestamp where the message should expire.
    """
    valid_blob_name = "channel1_thread1_1632492370.1234_guid.txt"
    ttl_seconds = 3600

    # Expected message timestamp extracted from the blob name
    expected_timestamp = 1632492370.1234

    # Simulate the current time to be more than 1 hour after the timestamp in the blob name
    simulated_current_time = expected_timestamp + ttl_seconds + 10  # Simulate 10 seconds past TTL

    # Debug: Print the split parts of the blob name to ensure correct format
    print(f"Blob name parts: {valid_blob_name.split('_')}")

    # First, verify that the timestamp is being extracted correctly
    extracted_timestamp = azure_blob_storage_queue_plugin.extract_message_id(valid_blob_name)
    assert extracted_timestamp == expected_timestamp, f"Expected timestamp: {expected_timestamp}, but got {extracted_timestamp}"

    # Now, patch the time and check if the message is expired
    with patch('time.time', return_value=simulated_current_time):
        expired = azure_blob_storage_queue_plugin.is_message_expired(valid_blob_name, ttl_seconds)
        assert expired, f"Expected message to be expired, but it was not. Current time: {simulated_current_time}, Message timestamp: {extracted_timestamp}"



@pytest.mark.asyncio
async def test_dequeue_message_network_error(azure_blob_storage_queue_plugin):
    """
    Test dequeue_message when a network error occurs during the deletion of a blob.
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    message_id = "1"
    guid = "test_guid"

    # Mock BlobClient
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_blob_client = mock_blob_service_client.get_blob_client.return_value

    # Simulate a network issue during deletion
    mock_blob_client.delete_blob.side_effect = Exception("Network issue")

    await azure_blob_storage_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id, guid)

    # Ensure the delete_blob method was called and the exception was logged
    mock_blob_client.delete_blob.assert_called_once()
    azure_blob_storage_queue_plugin.logger.error.assert_called_with("[AZURE_BLOB_QUEUE] Failed to dequeue message 'channel_1_thread_1_1_test_guid.txt': Network issue")

@pytest.mark.asyncio
async def test_cleanup_expired_messages_empty_queue(azure_blob_storage_queue_plugin):
    """
    Test cleanup_expired_messages when the queue is empty.
    """
    channel_id = "channel_1"
    thread_id = "thread_1"
    ttl_seconds = 3600

    # Mock list_blobs to return an empty list
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = []

    await azure_blob_storage_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)

    # Ensure no deletion was attempted
    mock_blob_service_client.get_blob_client.return_value.delete_blob.assert_not_called()

@pytest.mark.asyncio
async def test_cleanup_expired_messages_with_deletions(azure_blob_storage_queue_plugin):
    """
    Test cleanup_expired_messages where expired messages are found and deleted.
    """
    channel_id = "channel1"
    thread_id = "thread1"
    expired_blob = MagicMock()
    expired_blob.name = f"{channel_id}_{thread_id}_1632492370.1234_guid.txt"  # Expired

    ttl_seconds = 3600

    # Mock list_blobs to return blobs
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = [expired_blob]

    # Mock is_message_expired to return True for expired blobs
    with patch.object(azure_blob_storage_queue_plugin, 'is_message_expired', return_value=True):
        await azure_blob_storage_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)

    # Ensure delete_blob was called and removed_files_count was incremented
    mock_blob_service_client.get_blob_client.return_value.delete_blob.assert_called_once()
    azure_blob_storage_queue_plugin.logger.info.assert_any_call(f"[AZURE_BLOB_QUEUE] Expired message removed: {expired_blob.name}")

@pytest.mark.asyncio
async def test_has_older_messages_with_older_messages(azure_blob_storage_queue_plugin):
    """
    Test has_older_messages when there are older messages than the current one.
    """
    channel_id = "channel1"
    thread_id = "thread1"
    current_message_id = "1632492375"  # Current message timestamp

    # Mock list_blobs to return blobs
    older_blob_name = f"{channel_id}_{thread_id}_1632492370.1234_guid.txt"  # Older message
    current_blob_name = f"{channel_id}_{thread_id}_{current_message_id}.txt"  # Current message

    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = [
        MagicMock(name=older_blob_name),
        MagicMock(name=current_blob_name)
    ]

    # Run the function and assert it finds an older message
    has_older = await azure_blob_storage_queue_plugin.has_older_messages("messages", channel_id, thread_id, current_message_id)
    assert has_older is True

@pytest.mark.asyncio
async def test_clear_messages_queue(azure_blob_storage_queue_plugin):
    """
    Test clear_messages_queue where all messages for a given channel and thread are cleared.
    """
    channel_id = "channel1"
    thread_id = "thread1"

    # Mock list_blobs to return blobs specific to the channel and thread
    blob_names = [
        f"{channel_id}_{thread_id}_1_guid.txt",
        f"{channel_id}_{thread_id}_2_guid.txt"
    ]
    blobs = [MagicMock() for _ in blob_names]
    for blob, name in zip(blobs, blob_names):
        blob.name = name
    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client
    mock_container_client = mock_blob_service_client.get_container_client.return_value
    mock_container_client.list_blobs.return_value = blobs

    # Run the clear_messages_queue function
    await azure_blob_storage_queue_plugin.clear_messages_queue("messages", channel_id, thread_id)

    # Ensure delete_blob was called for each blob
    assert mock_blob_service_client.get_blob_client.return_value.delete_blob.call_count == len(blob_names)
    for blob_name in blob_names:
        azure_blob_storage_queue_plugin.logger.info.assert_any_call(f"[AZURE_BLOB_QUEUE] Message '{blob_name}' deleted successfully.")

@pytest.mark.asyncio
async def test_cleanup_multiple_queues(azure_blob_storage_queue_plugin):
    """
    Test cleanup_expired_messages across multiple queues and verify total_removed_files is incremented correctly.
    """
    ttl_mapping = {
        "messages": 3600,
        "internal_events": 3600,
        "external_events": 3600
    }

    expired_blob_name = "channel1_thread1_1632492370_guid.txt"  # Expired

    mock_blob_service_client = azure_blob_storage_queue_plugin.blob_service_client

    # Set up each queue to return one blob
    mock_blob_service_client.get_container_client.side_effect = [
        MagicMock(list_blobs=MagicMock(return_value=[MagicMock(name=expired_blob_name)])),
        MagicMock(list_blobs=MagicMock(return_value=[MagicMock(name=expired_blob_name)])),
        MagicMock(list_blobs=MagicMock(return_value=[MagicMock(name=expired_blob_name)]))
    ]

    # Mock is_message_expired to return True for all expired blobs
    with patch.object(azure_blob_storage_queue_plugin, 'is_message_expired', return_value=True):
        await azure_blob_storage_queue_plugin.clean_all_queues()

    # Ensure delete_blob was called for each queue
    assert mock_blob_service_client.get_blob_client.return_value.delete_blob.call_count == len(ttl_mapping)

    # Ensure the total removed files log is correct
    azure_blob_storage_queue_plugin.logger.info.assert_any_call(f"[AZURE_BLOB_QUEUE] Total removed expired messages across all containers: {len(ttl_mapping)}.")
