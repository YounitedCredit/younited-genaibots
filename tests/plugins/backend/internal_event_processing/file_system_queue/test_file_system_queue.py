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

    file_path = os.path.join("C:", "tmp", "test_queue", "messages", "channel_1_thread_1_1.txt")

    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        await file_system_queue_plugin.enqueue_message(
            "messages", channel_id, thread_id, message_id, message
        )

        mock_open.assert_called_once_with(file_path, 'w', encoding='utf-8')
        mock_file.write.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_dequeue_message(file_system_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    file_name = f"{channel_id}_{thread_id}_{message_id}.txt"

    file_path = os.path.join("C:", "tmp", "test_queue", "messages", file_name)

    with patch("os.path.exists", return_value=True) as mock_exists, patch("os.remove") as mock_remove:
        await file_system_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id)

    mock_exists.assert_called_once_with(file_path)
    mock_remove.assert_called_once_with(file_path)

@pytest.mark.asyncio
async def test_get_next_message(file_system_queue_plugin):
    current_message_id = "1632492373.1234"
    channel_id = "channel1"
    thread_id = "thread1"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"

    # Simulate files with Unix timestamps
    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_{next_message_id}.txt"]), \
         patch("builtins.open", mock_open(read_data=expected_content)) as mocked_file:

        # Call the get_next_message method
        result_message_id, result_content = await file_system_queue_plugin.get_next_message(
            "messages", channel_id, thread_id, current_message_id
        )

        # Verify that the correct message is retrieved
        assert result_message_id == next_message_id
        assert result_content == expected_content

        # Verify that the correct file was opened for reading
        expected_file_path = os.path.join(
            file_system_queue_plugin.root_directory,
            "messages",
            f"{channel_id}_{thread_id}_{next_message_id}.txt"
        )
        mocked_file.assert_called_once_with(expected_file_path, 'r', encoding='utf-8')

        # Verify that the file content was read
        mocked_file().read.assert_called_once()

@pytest.fixture
def temp_queue_dir():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after the test
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_get_next_message(file_system_queue_plugin, temp_queue_dir):
    # Setup
    file_system_queue_plugin.root_directory = temp_queue_dir
    file_system_queue_plugin.message_queue_container = "messages"
    os.makedirs(os.path.join(temp_queue_dir, "messages"), exist_ok=True)

    channel_id = "channel1"
    thread_id = "thread1"
    current_message_id = "1632492373.1234"
    next_message_id = "1632492374.5678"
    expected_content = "Next message content"

    # Create test files
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{current_message_id}.txt"), 'w') as f:
        f.write("Current message")
    with open(os.path.join(temp_queue_dir, "messages", f"{channel_id}_{thread_id}_{next_message_id}.txt"), 'w') as f:
        f.write(expected_content)

    # Test
    result_message_id, result_content = await file_system_queue_plugin.get_next_message(
        "messages", channel_id, thread_id, current_message_id
    )

    # Assert
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
