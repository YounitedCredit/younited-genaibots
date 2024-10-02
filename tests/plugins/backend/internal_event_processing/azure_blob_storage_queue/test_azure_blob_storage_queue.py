import os
import pytest
import logging  # Add this import
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from plugins.backend.internal_queue_processing.azure_blob_storage_queue.azure_blob_storage_queue import AzureBlobStorageQueuePlugin
from core.global_manager import GlobalManager
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from plugins.backend.internal_queue_processing.azure_blob_storage_queue.azure_blob_storage_queue import AZURE_BLOB_STORAGE_QUEUE


@pytest.fixture
def plugin(mock_global_manager):
    return AzureBlobStorageQueuePlugin(global_manager=mock_global_manager)

@patch('azure.storage.blob.BlobServiceClient')
def test_initialize_success(mock_blob_service_client, plugin):
    # Arrange
    mock_blob_service_client.return_value = MagicMock()
    mock_container_client = MagicMock()
    mock_blob_service_client.return_value.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True

    # Act
    plugin.initialize()

    # Assert
    mock_blob_service_client.assert_called_once()
    assert plugin.blob_service_client is not None
    plugin.logger.info.assert_any_call(
        '[AZURE_BLOB_QUEUE] BlobServiceClient successfully created'
    )
    
    # Check if get_container_client was called for each container
    expected_containers = [
        plugin.messages_queue,
        plugin.internal_events_queue,
        plugin.external_events_queue,
        plugin.wait_queue
    ]
    for container in expected_containers:
        mock_blob_service_client.return_value.get_container_client.assert_any_call(container)
        plugin.logger.info.assert_any_call(f'[AZURE_BLOB_QUEUE] Container already exists: {container}')

@patch('azure.storage.blob.BlobServiceClient')
def test_initialize_failure(mock_blob_service_client, plugin):
    # Arrange
    mock_blob_service_client.side_effect = Exception("Connection error")

    # Act and Assert
    with pytest.raises(Exception, match="Connection error"):
        plugin.initialize()

    plugin.logger.error.assert_called_with('[AZURE_BLOB_QUEUE] Failed to create BlobServiceClient: Connection error')

def test_extract_message_id_success(plugin):
    # Arrange
    blob_name = "channel_123_thread_456_1633016400.txt"

    # Act
    message_id = plugin.extract_message_id(blob_name)

    # Assert
    assert message_id == 1633016400.0

def test_extract_message_id_failure(plugin):
    # Arrange
    blob_name = "invalid_blob_name.txt"

    # Act
    message_id = plugin.extract_message_id(blob_name)

    # Assert
    assert message_id is None
    plugin.logger.warning.assert_called_with('[AZURE_BLOB_QUEUE] Failed to extract message ID from blob name: invalid_blob_name.txt')

def test_is_message_expired_expired(plugin, monkeypatch):
    # Arrange
    blob_name = "channel_123_thread_456_1633016400.txt"
    ttl_seconds = 3600

    # Mock the current time using monkeypatch
    monkeypatch.setattr('time.time', lambda: 1633020000)  # Set time to simulate expiration

    # Act
    expired = plugin.is_message_expired(blob_name, ttl_seconds)

    # Assert
    assert expired is True
    plugin.logger.info.assert_called_with(
        "[AZURE_BLOB_QUEUE] Message channel_123_thread_456_1633016400.txt has expired. TTL: 3600 seconds."
    )


def test_is_message_expired_not_expired(plugin, monkeypatch):
    # Arrange
    blob_name = "channel_123_thread_456_1633016400.txt"
    ttl_seconds = 3600

    # Mock the current time using monkeypatch to simulate a time before expiration
    monkeypatch.setattr('time.time', lambda: 1633016500)

    # Act
    expired = plugin.is_message_expired(blob_name, ttl_seconds)

    # Assert
    assert expired is False

@pytest.mark.asyncio
@patch('azure.storage.blob.BlobServiceClient')
async def test_enqueue_message_success(plugin, mock_blob_service_client):
    # Arrange
    mock_blob_client = MagicMock()
    mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    data_container = "test_container"
    channel_id = "123"
    thread_id = "456"
    message_id = "789"
    message = "test message"
    
    # Act
    await plugin.enqueue_message(data_container, channel_id, thread_id, message_id, message)

    # Assert
    plugin.logger.info.assert_called_with(f"[AZURE_BLOB_QUEUE] Enqueueing message for channel '123', thread '456' with GUID")
    mock_blob_client.upload_blob.assert_called_once_with(message, overwrite=True)

@pytest.mark.asyncio
@patch('azure.storage.blob.BlobServiceClient')
async def test_enqueue_message_exists(plugin, mock_blob_service_client):
    # Arrange
    mock_blob_client = MagicMock()
    mock_blob_client.upload_blob.side_effect = ResourceExistsError
    mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    data_container = "test_container"
    channel_id = "123"
    thread_id = "456"
    message_id = "789"
    message = "test message"
    
    # Act
    await plugin.enqueue_message(data_container, channel_id, thread_id, message_id, message)

    # Assert
    plugin.logger.warning.assert_called_with(f"[AZURE_BLOB_QUEUE] Message with GUID")

@pytest.mark.asyncio
@patch('azure.storage.blob.BlobServiceClient')
async def test_dequeue_message_success(plugin, mock_blob_service_client):
    # Arrange
    mock_blob_client = MagicMock()
    mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    data_container = "test_container"
    channel_id = "123"
    thread_id = "456"
    message_id = "789"
    guid = "some-guid"
    
    # Act
    await plugin.dequeue_message(data_container, channel_id, thread_id, message_id, guid)

    # Assert
    plugin.logger.info.assert_called_with(f"[AZURE_BLOB_QUEUE] Dequeueing message '{channel_id}_{thread_id}_{message_id}_{guid}.txt'")
    mock_blob_client.delete_blob.assert_called_once()

@pytest.mark.asyncio
@patch('azure.storage.blob.BlobServiceClient')
async def test_dequeue_message_not_found(plugin, mock_blob_service_client):
    # Arrange
    mock_blob_client = MagicMock()
    mock_blob_client.delete_blob.side_effect = ResourceNotFoundError
    mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    data_container = "test_container"
    channel_id = "123"
    thread_id = "456"
    message_id = "789"
    guid = "some-guid"

    # Act
    await plugin.dequeue_message(data_container, channel_id, thread_id, message_id, guid)

    # Assert
    plugin.logger.warning.assert_called_with(f"[AZURE_BLOB_QUEUE] Message '{channel_id}_{thread_id}_{message_id}_{guid}.txt' not found.")
