from unittest.mock import MagicMock, create_autospec, patch

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
