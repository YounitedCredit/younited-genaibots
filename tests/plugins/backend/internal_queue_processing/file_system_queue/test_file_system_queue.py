import os
import shutil
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from plugins.backend.internal_queue_processing.file_system_queue.file_system_queue import (
    FileSystemQueuePlugin,
)


@pytest.fixture
def file_system_queue_plugin(mock_global_manager, mock_file_system_config):
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
        "FILE_SYSTEM_QUEUE": mock_file_system_config
    }
    plugin = FileSystemQueuePlugin(mock_global_manager)
    plugin.initialize()
    return plugin

@pytest.fixture
def mock_file_system_config():
    return {
        "PLUGIN_NAME": "file_system_queue",
        "FILE_SYSTEM_QUEUE_DIRECTORY": os.path.join("C:", "tmp", "test_queue"),
        "FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER": "messages",
        "FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER": "internal_events",
        "FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER": "external_events",
        "FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER": "wait",
        "FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_TTL": 3600,
        "FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_TTL": 3600,
        "FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL": 3600,
        "FILE_SYSTEM_QUEUE_WAIT_QUEUE_TTL": 3600,
    }

def test_initialize(file_system_queue_plugin, mock_file_system_config):
    with patch('os.makedirs') as mock_makedirs:
        file_system_queue_plugin.initialize()

    messages_path = os.path.join("C:", "tmp", "test_queue", "messages")
    internal_events_path = os.path.join("C:", "tmp", "test_queue", "internal_events")
    external_events_path = os.path.join("C:", "tmp", "test_queue", "external_events")
    wait_path = os.path.join("C:", "tmp", "test_queue", "wait")

    mock_makedirs.assert_any_call(messages_path, exist_ok=True)
    mock_makedirs.assert_any_call(internal_events_path, exist_ok=True)
    mock_makedirs.assert_any_call(external_events_path, exist_ok=True)
    mock_makedirs.assert_any_call(wait_path, exist_ok=True)

    assert file_system_queue_plugin.plugin_name == "file_system_queue"

@pytest.mark.asyncio
async def test_enqueue_message(file_system_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    message = "Test Message"

    # Update the path to include the GUID
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        await file_system_queue_plugin.enqueue_message(
            "messages", channel_id, thread_id, message_id, message
        )

        # Modify assertion to check that the GUID part is present in the filename
        assert mock_open.call_args[0][0].startswith(os.path.join("C:", "tmp", "test_queue", "messages", "channel_1_thread_1_1_"))
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_dequeue_message(file_system_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    guid = "some-guid"  # Add the missing guid
    file_name = f"{channel_id}_{thread_id}_{message_id}_{guid}.txt"

    file_path = os.path.join("C:", "tmp", "test_queue", "messages", file_name)

    with patch("os.path.exists", return_value=True) as mock_exists, patch("os.remove") as mock_remove:
        await file_system_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id, guid)

    mock_exists.assert_called_once_with(file_path)
    mock_remove.assert_called_once_with(file_path)

@pytest.mark.asyncio
async def test_get_next_message(file_system_queue_plugin):
    current_message_id = "1632492373.1234"
    channel_id = "channel1"
    thread_id = "thread1"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"
    current_guid = "current-guid"
    next_guid = "next-guid"

    # Simulate a directory with multiple message files including GUIDs
    file_list = [
        f"{channel_id}_{thread_id}_1632492371.0000_earlier-guid.txt",  # Earlier message
        f"{channel_id}_{thread_id}_{current_message_id}_{current_guid}.txt",  # Current message
        f"{channel_id}_{thread_id}_{next_message_id}_{next_guid}.txt"  # Next message
    ]

    # Patch to mock directory listing and file reading
    with patch("os.listdir", return_value=file_list), \
         patch("builtins.open", mock_open(read_data=expected_content)) as mocked_file:

        result_message_id, result_content = await file_system_queue_plugin.get_next_message(
            "messages", channel_id, thread_id, current_message_id
        )

        # Assert that the next message ID and content are returned correctly
        assert result_message_id == next_message_id
        assert result_content == expected_content

@pytest.mark.asyncio
async def test_get_next_message_integration(file_system_queue_plugin, temp_queue_dir):
    file_system_queue_plugin.root_directory = temp_queue_dir
    file_system_queue_plugin.message_queue_container = "messages"
    os.makedirs(os.path.join(temp_queue_dir, "messages"), exist_ok=True)

    channel_id = "channel1"
    thread_id = "thread1"
    current_message_id = "1632492373.1234"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"
    current_guid = "current-guid"
    next_guid = "next-guid"

    # Create multiple test files in the directory with GUIDs
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_1632492371.0000_earlier-guid.txt"), 'w') as f:
        f.write("Earlier message")
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{current_message_id}_{current_guid}.txt"), 'w') as f:
        f.write("Current message")
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{next_message_id}_{next_guid}.txt"), 'w') as f:
        f.write(expected_content)

    result_message_id, result_content = await file_system_queue_plugin.get_next_message(
        "messages", channel_id, thread_id, current_message_id
    )

    # Assert that the next message was retrieved correctly
    assert result_message_id == next_message_id
    assert result_content == expected_content

@pytest.fixture
def temp_queue_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_get_next_message_integration(file_system_queue_plugin, temp_queue_dir):
    file_system_queue_plugin.root_directory = temp_queue_dir
    file_system_queue_plugin.message_queue_container = "messages"
    os.makedirs(os.path.join(temp_queue_dir, "messages"), exist_ok=True)

    channel_id = "channel1"
    thread_id = "thread1"
    current_message_id = "1632492373.1234"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"
    current_guid = "current-guid"
    next_guid = "next-guid"

    # Create files with both the message_id and guid
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{current_message_id}_{current_guid}.txt"), 'w') as f:
        f.write("Current message")
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{next_message_id}_{next_guid}.txt"), 'w') as f:
        f.write(expected_content)

    result_message_id, result_content = await file_system_queue_plugin.get_next_message(
        "messages", channel_id, thread_id, current_message_id
    )

    # Assert that the next message ID and content are returned correctly
    assert result_message_id == next_message_id
    assert result_content == expected_content


@pytest.mark.asyncio
async def test_clear_messages_queue(file_system_queue_plugin):
    channel_id = "channel_1"
    thread_id = "thread_1"

    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_1.txt", f"{channel_id}_{thread_id}_2.txt"]), \
         patch("os.remove") as mock_remove:

        await file_system_queue_plugin.clear_messages_queue("messages", channel_id, thread_id)

    assert mock_remove.call_count == 2

@pytest.mark.asyncio
async def test_cleanup_expired_messages(file_system_queue_plugin, temp_queue_dir):
    file_system_queue_plugin.root_directory = temp_queue_dir
    file_system_queue_plugin.message_queue_container = "messages"
    os.makedirs(os.path.join(temp_queue_dir, "messages"), exist_ok=True)

    channel_id = "channel1"
    thread_id = "thread1"
    expired_message_id = "1632492370.1234"  # Older timestamp
    valid_message_id = "1632492374.5678"
    expired_guid = "expired-guid"
    valid_guid = "valid-guid"

    expired_content = "Expired message"
    valid_content = "Valid message"
    ttl_seconds = 3600

    # Include GUID in the filenames
    expired_message_path = os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{expired_message_id}_{expired_guid}.txt")
    valid_message_path = os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{valid_message_id}_{valid_guid}.txt")

    # Create test files for expired and valid messages
    with open(expired_message_path, 'w') as f:
        f.write(expired_content)
    with open(valid_message_path, 'w') as f:
        f.write(valid_content)

    # Mock time to simulate that the expired message has exceeded the TTL
    with patch('time.time', return_value=float(expired_message_id) + ttl_seconds + 1):  # Simulate time passing
        await file_system_queue_plugin.cleanup_expired_messages("messages", channel_id, thread_id, ttl_seconds)

    # Verify the expired message was removed and the valid one was not
    assert not os.path.exists(expired_message_path)
    assert os.path.exists(valid_message_path)

@pytest.mark.asyncio
async def test_clear_all_queues(file_system_queue_plugin):
    with patch("os.listdir", return_value=["file1.txt", "file2.txt"]), patch("os.remove") as mock_remove:
        await file_system_queue_plugin.clear_all_queues()

    # Make sure only two files were expected for removal
    assert mock_remove.call_count == 8  # Adjust the expected count if needed
