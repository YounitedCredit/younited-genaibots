import os
import pytest
from unittest.mock import patch, MagicMock

from plugins.backend.internal_queue_processing.file_system_queue.file_system_queue import FileSystemQueuePlugin

@pytest.fixture
def file_system_queue_plugin(mock_global_manager, mock_file_system_config):
    # Simulez le dictionnaire de configuration complet et correct
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_QUEUE_PROCESSING = {
        "FILE_SYSTEM_QUEUE": mock_file_system_config
    }
    plugin = FileSystemQueuePlugin(mock_global_manager)
    plugin.initialize()  # Assurez-vous que l'initialisation est effectuée avant chaque test
    return plugin

@pytest.fixture
def mock_file_system_config():
    # Fournissez toutes les valeurs nécessaires pour éviter les erreurs de validation
    return {
        "PLUGIN_NAME": "file_system_queue",
        "FILE_SYSTEM_QUEUE_DIRECTORY": os.path.join("C:", "tmp", "test_queue"),
        "FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER": "messages",
        "FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER": "internal_events",
        "FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER": "external_events",
        "FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER": "wait",
    }

def test_initialize(file_system_queue_plugin, mock_file_system_config):
    # Run the initialize method
    with patch('os.makedirs') as mock_makedirs:
        file_system_queue_plugin.initialize()

    # Construction dynamique des chemins
    messages_path = os.path.join("C:", "tmp", "test_queue", "messages")
    internal_events_path = os.path.join("C:", "tmp", "test_queue", "internal_events")
    external_events_path = os.path.join("C:", "tmp", "test_queue", "external_events")
    wait_path = os.path.join("C:", "tmp", "test_queue", "wait")

    # Assert that the necessary directories are created
    mock_makedirs.assert_any_call(messages_path, exist_ok=True)
    mock_makedirs.assert_any_call(internal_events_path, exist_ok=True)
    mock_makedirs.assert_any_call(external_events_path, exist_ok=True)
    mock_makedirs.assert_any_call(wait_path, exist_ok=True)

    # Assert that the plugin name is correctly set
    assert file_system_queue_plugin.plugin_name == "file_system_queue"

@pytest.mark.asyncio
async def test_enqueue_message(file_system_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    message = "Test Message"

    # Construction du chemin du fichier en fonction de la plateforme
    file_path = os.path.join("C:", "tmp", "test_queue", "messages", "channel_1_thread_1_1.txt")

    # Mock the open function
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        await file_system_queue_plugin.enqueue_message(
            "messages", channel_id, thread_id, message_id, message
        )

        # Assert that the message was written to the correct file
        mock_open.assert_called_once_with(file_path, 'w', encoding='utf-8')
        mock_file.write.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_dequeue_message(file_system_queue_plugin):
    message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"
    file_name = f"{channel_id}_{thread_id}_{message_id}.txt"

    # Construction du chemin du fichier
    file_path = os.path.join("C:", "tmp", "test_queue", "messages", file_name)

    # Mock os.path.exists and os.remove
    with patch("os.path.exists", return_value=True) as mock_exists, patch("os.remove") as mock_remove:
        await file_system_queue_plugin.dequeue_message("messages", channel_id, thread_id, message_id)

    mock_exists.assert_called_once_with(file_path)
    mock_remove.assert_called_once_with(file_path)

@pytest.mark.asyncio
async def test_get_next_message(file_system_queue_plugin):
    current_message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"

    # Mock os.listdir and open
    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_2.txt"]), \
         patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_file.read.return_value = "Next message content"
        mock_open.return_value.__enter__.return_value = mock_file

        next_message_id, message_content = await file_system_queue_plugin.get_next_message(
            "messages", channel_id, thread_id, current_message_id
        )

        # Assert the next message is retrieved correctly
        assert next_message_id == "2"
        assert message_content == "Next message content"
        mock_open().read.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_messages(file_system_queue_plugin):
    channel_id = "channel_1"
    thread_id = "thread_1"

    # Mock os.listdir and open
    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_1.txt", f"{channel_id}_{thread_id}_2.txt"]), \
         patch("builtins.open", new_callable=MagicMock) as mock_open:

        messages = await file_system_queue_plugin.get_all_messages("messages", channel_id, thread_id)

    # Assert both messages are retrieved
    assert len(messages) == 2
    assert mock_open().read.call_count == 2

@pytest.mark.asyncio
async def test_has_older_messages(file_system_queue_plugin):
    current_message_id = "1"
    channel_id = "channel_1"
    thread_id = "thread_1"

    # Mock os.listdir
    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_2.txt"]):
        has_older = await file_system_queue_plugin.has_older_messages("messages", channel_id, thread_id, current_message_id)

    # Assert that there are older messages
    assert has_older

@pytest.mark.asyncio
async def test_clear_messages_queue(file_system_queue_plugin):
    channel_id = "channel_1"
    thread_id = "thread_1"

    # Mock os.listdir and os.remove
    with patch("os.listdir", return_value=[f"{channel_id}_{thread_id}_1.txt", f"{channel_id}_{thread_id}_2.txt"]), \
         patch("os.remove") as mock_remove:

        await file_system_queue_plugin.clear_messages_queue("messages", channel_id, thread_id)

    # Assert that all relevant messages are removed
    assert mock_remove.call_count == 2