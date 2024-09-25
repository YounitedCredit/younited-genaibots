import json
import os
from unittest.mock import AsyncMock, call, mock_open, patch
import time
import pytest

from core.backend.pricing_data import PricingData
from plugins.backend.internal_data_processing.file_system.file_system import (
    FileSystemPlugin,
)


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "file_system",
        "FILE_SYSTEM_DIRECTORY": "/test_directory",
        "FILE_SYSTEM_SESSIONS_CONTAINER": "sessions",
        "FILE_SYSTEM_MESSAGES_CONTAINER": "messages",
        "FILE_SYSTEM_FEEDBACKS_CONTAINER": "feedbacks",
        "FILE_SYSTEM_CONCATENATE_CONTAINER": "concatenate",
        "FILE_SYSTEM_PROMPTS_CONTAINER": "prompts",
        "FILE_SYSTEM_COSTS_CONTAINER": "costs",
        "FILE_SYSTEM_PROCESSING_CONTAINER": "processing",
        "FILE_SYSTEM_ABORT_CONTAINER": "abort",
        "FILE_SYSTEM_VECTORS_CONTAINER": "vectors",
        "FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER": "custom_actions",
        "FILE_SYSTEM_SUBPROMPTS_CONTAINER": "subprompts",
        "FILE_SYSTEM_MESSAGES_QUEUE_CONTAINER": "messages_queue"
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING = {
        "FILE_SYSTEM": mock_config
    }
    return mock_global_manager

@pytest.fixture
def file_system_plugin(extended_mock_global_manager):
    plugin = FileSystemPlugin(global_manager=extended_mock_global_manager)
    with patch("os.makedirs"):
        plugin.initialize()
    return plugin

def test_file_system_properties(file_system_plugin):
    assert file_system_plugin.plugin_name == "file_system"
    assert file_system_plugin.sessions == file_system_plugin.sessions_container
    assert file_system_plugin.feedbacks == file_system_plugin.feedbacks_container
    assert file_system_plugin.concatenate == file_system_plugin.concatenate_container
    assert file_system_plugin.prompts == file_system_plugin.prompts_container
    assert file_system_plugin.costs == file_system_plugin.costs_container
    assert file_system_plugin.processing == file_system_plugin.processing_container
    assert file_system_plugin.abort == file_system_plugin.abort_container
    assert file_system_plugin.vectors == file_system_plugin.vectors_container
    assert file_system_plugin.custom_actions == file_system_plugin.custom_actions_container
    assert file_system_plugin.subprompts == file_system_plugin.subprompts_container
    assert file_system_plugin.messages_queue == file_system_plugin.message_queue_container

def test_init_shares_permission_error(file_system_plugin):
    with patch("os.makedirs", side_effect=OSError("Permission denied")), pytest.raises(OSError):
        file_system_plugin.init_shares()

@pytest.mark.asyncio
async def test_read_data_content(file_system_plugin):
    m = mock_open(read_data='{"key": "value"}')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        content = await file_system_plugin.read_data_content('container', 'file')
        assert content == '{"key": "value"}'
        m.assert_called_once_with(
            os.path.join(file_system_plugin.root_directory, 'container', 'file'),
            'r', encoding='utf-8', errors='ignore'
        )

@pytest.mark.asyncio
async def test_read_data_content_file_not_exists(file_system_plugin):
    with patch("os.path.exists", return_value=False):
        content = await file_system_plugin.read_data_content('container', 'file')
        assert content is None

@pytest.mark.asyncio
async def test_write_data_content(file_system_plugin):
    m = mock_open()
    with patch("builtins.open", m):
        await file_system_plugin.write_data_content('container', 'file', '{"key": "value"}')
        m.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'), 'w')
        m().write.assert_called_once_with('{"key": "value"}')

@pytest.mark.asyncio
async def test_remove_data_content(file_system_plugin):
    with patch("os.path.exists", return_value=True), patch("os.remove", new_callable=AsyncMock) as mock_remove:
        await file_system_plugin.remove_data_content('container', 'file')
        mock_remove.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'))

@pytest.mark.asyncio
async def test_remove_data_content_file_not_exists(file_system_plugin):
    with patch("os.path.exists", return_value=False), patch("os.remove", new_callable=AsyncMock) as mock_remove:
        await file_system_plugin.remove_data_content('container', 'file')
        mock_remove.assert_not_called()

@patch('os.makedirs')
def test_init_shares(mock_makedirs, file_system_plugin):
    file_system_plugin.init_shares()
    assert mock_makedirs.call_count == 11


pytest.mark.asyncio
async def test_append_data(file_system_plugin, mocker):
    # Simule l'ouverture du fichier en mode append ('a')
    m = mock_open()

    # Patch 'os.path.join' pour s'assurer qu'il renvoie un chemin cohérent
    mocker.patch("os.path.join", return_value="/mocked/root/container/file")

    # Patch 'open' pour utiliser notre mock_open
    with patch("builtins.open", m):
        # Appel à la méthode append_data avec les nouvelles données
        await file_system_plugin.append_data('container', 'file', 'data')

        # Vérifie que le fichier est bien ouvert en mode append ('a')
        m.assert_called_once_with("/mocked/root/container/file", 'a', encoding='utf-8')

        # Vérifie que les données ont bien été écrites dans le fichier en deux appels
        m().write.assert_has_calls([call('data'), call('\n')])

@pytest.mark.asyncio
async def test_update_pricing(file_system_plugin):
    m = mock_open(read_data='{"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50, "total_cost": 1.0, "input_cost": 0.5, "output_cost": 0.5}')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True), patch("json.dump") as mock_dump:
        new_pricing = PricingData(total_tokens=50, prompt_tokens=25, completion_tokens=25, total_cost=0.5, input_cost=0.25, output_cost=0.25)
        updated_data = await file_system_plugin.update_pricing("container", "file", new_pricing)
        assert updated_data.total_tokens == 150
        assert updated_data.total_cost == 1.5
        mock_dump.assert_called_once()

@pytest.mark.asyncio
async def test_update_prompt_system_message(file_system_plugin):
    m = mock_open(read_data='[{"role": "system", "content": "old"}, {"role": "user", "content": "hello"}]')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True), patch("json.dump") as mock_dump:
        await file_system_plugin.update_prompt_system_message("channel", "thread", "new")
        mock_dump.assert_called_once()
        updated_content = mock_dump.call_args[0][0]
        assert updated_content[0]["content"] == "new"

@pytest.mark.asyncio
async def test_list_container_files(file_system_plugin):
    with patch("os.listdir", return_value=["file1.txt", "file2.json"]), patch("os.path.isfile", return_value=True):
        files = await file_system_plugin.list_container_files("container")
        assert files == ["file1", "file2"]

@pytest.mark.asyncio
async def test_update_session_new_file(file_system_plugin):
    # Define a container to capture written content
    written_data = []

    # Custom write function to simulate file writing and capture the content
    def custom_write(data):
        written_data.append(data)  # Append written content to the list

    # Mock the open function, and replace the 'write' method with the custom one
    m = mock_open()
    m().write.side_effect = custom_write

    # Patch 'open' and 'os.path.exists' to simulate file operations
    with patch("builtins.open", m), patch("os.path.exists", return_value=False):
        # Call the method to update the session
        await file_system_plugin.update_session("container", "file", "user", "test_content")

        # Check that `write` was called with the expected JSON structure
        expected_content = [{"role": "user", "content": "test_content"}]

        # Join all captured written data into one string (in case of multiple writes)
        written_content = ''.join(written_data)

        # Debugging: Print the written content for verification
        print(f"Written content: {written_content}")

        # Manually parse the written content to check if it matches the expected data
        assert json.loads(written_content) == expected_content

@pytest.mark.asyncio
async def test_update_session_existing_file(file_system_plugin):
    # Mocking the open function to simulate reading an existing file and writing to it
    m = mock_open(read_data='[{"role": "system", "content": "existing_content"}]')

    # List to capture written data
    written_data = []

    # Custom write function to append written data to the list
    def custom_write(data):
        written_data.append(data)

    # Use the mock_open with the custom write
    m().write.side_effect = custom_write

    # Patch 'open' and 'os.path.exists' to simulate file operations
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        # Call the method to update the session
        await file_system_plugin.update_session("container", "file", "user", "new_content")

        # Check if file was opened in write mode
        m.assert_called_with(os.path.join(file_system_plugin.root_directory, "container", "file"), 'w')

        # Join all the written data to simulate what would have been written to the file
        written_content = ''.join(written_data)

        # Debugging: Print the written content for verification
        print(f"Written content: {written_content}")

        # Parse the written content and assert it matches the expected JSON structure
        expected_content = [
            {"role": "system", "content": "existing_content"},
            {"role": "user", "content": "new_content"}
        ]
        assert json.loads(written_content) == expected_content

def test_validate_request_raises_not_implemented(file_system_plugin):
    with pytest.raises(NotImplementedError):
        file_system_plugin.validate_request(None)

def test_handle_request_raises_not_implemented(file_system_plugin):
    with pytest.raises(NotImplementedError):
        file_system_plugin.handle_request(None)

@patch("os.makedirs", side_effect=OSError("Permission denied"))
def test_init_shares_error(mock_makedirs, mock_global_manager, file_system_plugin):
    with pytest.raises(OSError, match="Permission denied"):
        file_system_plugin.init_shares()

    # Create a mock directory for testing
    expected_directory = os.path.join("/test_directory", "sessions")
    expected_message = f"Failed to create directory: {expected_directory} - Permission denied"

    # Check if the logger was called with the expected error message
    mock_global_manager.logger.error.assert_called_once_with(expected_message)

@pytest.mark.asyncio
async def test_read_data_content_unicode_error(file_system_plugin):
    # Simulate a UnicodeDecodeError while reading a file
    m = mock_open()
    m.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "reason")
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        content = await file_system_plugin.read_data_content('container', 'file')
        assert content is None

@pytest.mark.asyncio
async def test_append_data_io_error(file_system_plugin):
    # Simulate an IOError when appending data
    m = mock_open()
    m.side_effect = IOError("Unable to open file")
    with patch("builtins.open", m), patch("os.path.join", return_value="/mocked/path"):
        with pytest.raises(IOError, match="Unable to open file"):
            await file_system_plugin.append_data('container', 'file', 'data')

@pytest.mark.asyncio
async def test_remove_data_content_os_error(file_system_plugin):
    # Simulate an OSError while trying to remove a file
    with patch("os.path.exists", return_value=True), patch("os.remove", side_effect=OSError("Permission denied")) as mock_remove:
        with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
            await file_system_plugin.remove_data_content('container', 'file')
            mock_remove.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'))
            mock_logger_error.assert_called_once_with("Failed to delete file: Permission denied")

@pytest.mark.asyncio
async def test_update_pricing_file_not_exists(file_system_plugin):
    # Test the update_pricing when the file doesn't exist
    with patch("os.path.exists", return_value=False), patch("builtins.open", mock_open()), patch("json.dump") as mock_dump:
        new_pricing = PricingData(total_tokens=50, prompt_tokens=25, completion_tokens=25, total_cost=0.5, input_cost=0.25, output_cost=0.25)
        updated_data = await file_system_plugin.update_pricing("container", "file", new_pricing)
        assert updated_data.total_tokens == 50
        assert updated_data.total_cost == 0.5
        mock_dump.assert_called_once()

@pytest.mark.asyncio
async def test_enqueue_message_io_error(file_system_plugin):
    # Simulate an IOError when writing the message to the queue
    m = mock_open()
    m.side_effect = IOError("Write error")
    with patch("builtins.open", m), patch("os.path.join", return_value="/mocked/path"):
        with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
            await file_system_plugin.enqueue_message('channel', 'thread', 'message_id', 'message')
            mock_logger_error.assert_called_once_with("Failed to enqueue the message for channel 'channel', thread 'thread': Write error")


@pytest.mark.asyncio
async def test_get_next_message_no_files(file_system_plugin):
    # Simulate no files found in the container
    with patch("os.listdir", return_value=[]):
        next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', 'current_id')
        assert next_message_id is None
        assert message_content is None

@pytest.mark.asyncio
async def test_get_all_messages_empty(file_system_plugin):
    # Simulate an empty container
    with patch("os.listdir", return_value=[]):
        messages = await file_system_plugin.get_all_messages('channel', 'thread')
        assert messages == []

@pytest.mark.asyncio
async def test_get_next_message_no_match(file_system_plugin):
    # Simulate finding files but no match for the next message
    with patch("os.listdir", return_value=["channel_1_100.txt", "channel_1_200.txt"]), patch("os.path.exists", return_value=True):
        next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', '300')
        assert next_message_id is None
        assert message_content is None

@pytest.mark.asyncio
async def test_clear_messages_queue_no_path(file_system_plugin):
    # Simulate the queue directory not existing
    with patch("os.path.exists", return_value=False):
        await file_system_plugin.clear_messages_queue('channel', 'thread')

import os
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_clear_messages_queue_error_deleting(file_system_plugin):
    # Simule une erreur lors de la suppression d'un fichier
    with patch("os.path.exists", return_value=True), patch("os.listdir", return_value=["channel_thread_1.txt"]), patch("os.remove", side_effect=OSError("Delete error")):
        with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
            await file_system_plugin.clear_messages_queue('channel', 'thread')
            
            # Générer le chemin attendu en utilisant os.path.join
            expected_path = os.path.join("/test_directory", "messages_queue", "channel_thread_1.txt")
            
            # Normaliser le chemin attendu
            normalized_expected_path = os.path.normpath(expected_path)
            
            # Construire le message de log attendu
            expected_log_message = f"Failed to delete message file '{normalized_expected_path}': Delete error"
            
            # Normaliser les séparateurs dans le message attendu
            normalized_expected_log_message = expected_log_message.replace('\\', os.path.sep).replace('/', os.path.sep)

            # Capturer le message de log appelé
            actual_call_args = mock_logger_error.call_args[0][0]
            
            # Normaliser le message capturé
            normalized_actual_log_message = actual_call_args.replace('\\', os.path.sep).replace('/', os.path.sep)

            # Vérifier que les deux messages normalisés sont égaux
            assert normalized_actual_log_message == normalized_expected_log_message

@pytest.mark.asyncio
async def test_read_data_content_io_error(file_system_plugin):
    m = mock_open()
    m.side_effect = IOError("File read error")
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        content = await file_system_plugin.read_data_content('container', 'file')
        assert content is None

@pytest.mark.asyncio
async def test_remove_data_content_logs_error(file_system_plugin):
    with patch("os.path.exists", return_value=True), patch("os.remove", side_effect=OSError("Permission denied")):
        with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
            await file_system_plugin.remove_data_content('container', 'file')
            mock_logger_error.assert_called_once_with("Failed to delete file: Permission denied")

@pytest.mark.asyncio
async def test_write_data_content_calls_open(file_system_plugin):
    m = mock_open()
    with patch("builtins.open", m):
        await file_system_plugin.write_data_content('container', 'file', '{"key": "value"}')
        m.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'), 'w')

@pytest.mark.asyncio
async def test_write_read_remove_data_integration(file_system_plugin):
    # Créez le répertoire si nécessaire avant l'écriture
    file_path = os.path.join(file_system_plugin.root_directory, 'container', 'file')
    directory_path = os.path.dirname(file_path)
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    # Écriture de données
    await file_system_plugin.write_data_content('container', 'file', '{"key": "value"}')

    # Vérifiez si le fichier a été correctement écrit en vérifiant l'existence du fichier
    assert os.path.exists(file_path), f"Le fichier n'existe pas : {file_path}"

    # Lecture des données
    content = await file_system_plugin.read_data_content('container', 'file')
    assert content == '{"key": "value"}', f"Contenu incorrect: {content}"

    # Suppression des données
    await file_system_plugin.remove_data_content('container', 'file')

    # Vérification que les données ont bien été supprimées
    content_after_removal = await file_system_plugin.read_data_content('container', 'file')
    assert content_after_removal is None



@pytest.mark.asyncio
async def test_update_session_invalid_json(file_system_plugin):
    m = mock_open(read_data="invalid_json")
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        await file_system_plugin.update_session("container", "file", "user", "new_content")
        # Vérifie que rien n'est écrit dans le fichier en cas de JSON invalide
        m().write.assert_not_called()

async def has_older_messages(self, channel_id: str, thread_id: str) -> bool:
    self.logger.info(f"Checking for older messages in channel '{channel_id}', thread '{thread_id}'")
    try:
        current_time = int(time.time())
        queue_path = os.path.join(self.root_directory, self.message_queue_container)
        files = os.listdir(queue_path)

        # Filtrer les fichiers pour le channel_id et thread_id spécifique
        filtered_files = [f for f in files if f.startswith(f"{channel_id}_{thread_id}")]
        self.logger.info(f"Found {len(filtered_files)} messages for channel '{channel_id}', thread '{thread_id}'")

        if not filtered_files:
            self.logger.info(f"No pending messages found for channel '{channel_id}', thread '{thread_id}'.")
            return False

        message_ttl = self.global_manager.bot_config.MESSAGE_QUEUING_TTL

        # Check for messages older than message_ttl
        for file_name in filtered_files:
            try:
                # Extract the message_id (timestamp) from the filename
                message_id = file_name.split('_')[-1].split('.')[0]
                timestamp = float(message_id)
                time_difference = current_time - timestamp

                self.logger.info(f"Message '{file_name}' has a timestamp of {timestamp}. Time difference: {time_difference} seconds.")

                if time_difference > message_ttl:
                    self.logger.info(f"Message '{file_name}' is older than TTL, dequeuing...")
                    await self.dequeue_message(channel_id=channel_id, thread_id=thread_id, message_id=message_id)
                    return True
            except ValueError:
                self.logger.error(f"Invalid message file format: {file_name}, skipping.")

        return False

    except Exception as e:
        self.logger.error(f"Failed to check for older messages: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_get_next_message(file_system_plugin, mocker):
    mocker.patch("os.listdir", return_value=["channel_thread_5341351.5343.txt", "channel_thread_5341352.5344.txt"])
    mocker.patch("os.path.exists", return_value=True)

    # Mock to open and return simulated content
    mock_open_file = mock_open(read_data='{"content": "test message"}')
    with patch("builtins.open", mock_open_file):
        # Ensure the 5341352.5344 file is processed after 5341351.5343
        next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', '5341351.5343')

        # Assert the correct next message ID and content
        assert next_message_id == "5341352.5344", f"Expected next_message_id to be '5341352.5344', but got {next_message_id}"
        assert message_content == '{"content": "test message"}'

@pytest.mark.asyncio
async def test_get_next_message_no_match(file_system_plugin, mocker):
    mocker.patch("os.listdir", return_value=["channel_1_999999.txt"])
    mocker.patch("os.path.exists", return_value=True)

    next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', '999999')
    assert next_message_id is None
    assert message_content is None

@pytest.mark.asyncio
async def test_get_next_message_exception(file_system_plugin, mocker):
    mocker.patch("os.listdir", side_effect=OSError("Directory not found"))

    next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', '999999')
    assert next_message_id is None
    assert message_content is None

@pytest.mark.asyncio
async def test_dequeue_message(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mock_remove = mocker.patch("os.remove")

    await file_system_plugin.dequeue_message('channel', 'thread', 'message_id')
    mock_remove.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'messages_queue', 'channel_thread_message_id.txt'))

@pytest.mark.asyncio
async def test_dequeue_message_file_not_found(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=False)
    mock_remove = mocker.patch("os.remove")

    await file_system_plugin.dequeue_message('channel', 'thread', 'message_id')
    mock_remove.assert_not_called()

@pytest.mark.asyncio
async def test_dequeue_message_exception(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mock_remove = mocker.patch("os.remove", side_effect=OSError("Permission denied"))

    with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
        await file_system_plugin.dequeue_message('channel', 'thread', 'message_id')
        mock_logger_error.assert_called_once_with("Failed to remove message 'message_id' from the queue: Permission denied")

@pytest.mark.asyncio
async def test_get_all_messages(file_system_plugin, mocker):
    # Mock the directory listing to return two files
    mocker.patch("os.listdir", return_value=["channel_thread_message_1.txt", "channel_thread_message_2.txt"])
    
    # Mock the file reading process with "message content"
    mock_open_file = mock_open(read_data="message content")
    
    with patch("builtins.open", mock_open_file):
        # Call the get_all_messages function
        messages = await file_system_plugin.get_all_messages('channel', 'thread')
        
        # Verify that two messages were read
        assert len(messages) == 2, f"Expected 2 messages, but got {len(messages)}"
        
        # Verify that both messages have the correct content
        assert messages[0] == "message content"
        assert messages[1] == "message content"

@pytest.mark.asyncio
async def test_get_all_messages_empty(file_system_plugin, mocker):
    mocker.patch("os.listdir", return_value=[])
    messages = await file_system_plugin.get_all_messages('channel', 'thread')
    assert messages == []

@pytest.mark.asyncio
async def test_get_all_messages_exception(file_system_plugin, mocker):
    mocker.patch("os.listdir", side_effect=OSError("Directory not found"))

    with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
        messages = await file_system_plugin.get_all_messages('channel', 'thread')
        assert messages == []
        mock_logger_error.assert_called_once_with("Failed to retrieve all messages for channel 'channel', thread 'thread': Directory not found")

@pytest.mark.asyncio
async def test_clear_messages_queue(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["channel_thread_1.txt"])
    mock_remove = mocker.patch("os.remove")

    await file_system_plugin.clear_messages_queue('channel', 'thread')
    mock_remove.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'messages_queue', 'channel_thread_1.txt'))

@pytest.mark.asyncio
async def test_clear_messages_queue_directory_not_exists(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=False)

    await file_system_plugin.clear_messages_queue('channel', 'thread')

    assert True  # Success if no exception is raised

@pytest.mark.asyncio
async def test_clear_messages_queue_exception(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["channel_thread_1.txt"])
    mock_remove = mocker.patch("os.remove", side_effect=OSError("Permission denied"))

    with patch.object(file_system_plugin.logger, 'error') as mock_logger_error:
        await file_system_plugin.clear_messages_queue('channel', 'thread')

        # Normalisation des chemins pour éviter les erreurs dues aux séparateurs
        expected_path = os.path.normpath("/test_directory/messages_queue/channel_thread_1.txt")
        expected_log_message = f"Failed to delete message file '{expected_path}': Permission denied"
        
        # Normaliser le message de log réel
        actual_log_message = mock_logger_error.call_args[0][0]
        assert os.path.normpath(actual_log_message) == expected_log_message

@pytest.mark.asyncio
async def test_has_older_messages(file_system_plugin, mocker):
    # Get the current time in Unix timestamp format
    current_time = time.time()
    
    # Create two timestamps: one older than the TTL and one newer
    old_timestamp = current_time - 200  # 200 seconds ago (older than the TTL)
    new_timestamp = current_time - 50   # 50 seconds ago (newer than the TTL)
    
    # Format the timestamps with full decimal precision
    old_timestamp_str = f"{old_timestamp:.6f}"
    new_timestamp_str = f"{new_timestamp:.6f}"
    
    # Mock current time to be fixed at `current_time`
    mocker.patch("time.time", return_value=current_time)
    
    # Mock file listing with Unix timestamps in the message filenames
    mocker.patch("os.listdir", return_value=[
        f"channel_thread_{old_timestamp_str}.txt",  # This file is older than TTL
        f"channel_thread_{new_timestamp_str}.txt",  # This file is newer than TTL
    ])
    
    # Mock file existence check
    mocker.patch("os.path.exists", return_value=True)
    
    # Mock the dequeue message method (for the older message)
    mock_dequeue = mocker.patch.object(file_system_plugin, 'dequeue_message', new_callable=AsyncMock)
    
    # Set the message TTL to 100 seconds
    file_system_plugin.global_manager.bot_config.MESSAGE_QUEUING_TTL = 100
    
    # Call the function to test whether older messages are found and dequeued
    result = await file_system_plugin.has_older_messages('channel', 'thread')
  
    # Assert that the result is True because there is still one valid message (newer one)
    assert result is True, f"Expected result to be True, but got {result}"


@pytest.mark.asyncio
async def test_get_next_message_no_match(file_system_plugin, mocker):
    mocker.patch("os.listdir", return_value=["channel_1_999999.txt"])
    mocker.patch("os.path.exists", return_value=True)

    next_message_id, message_content = await file_system_plugin.get_next_message('channel', 'thread', '999999')
    
    assert next_message_id is None
    assert message_content is None

@pytest.mark.asyncio
async def test_dequeue_message(file_system_plugin, mocker):
    mocker.patch("os.path.exists", return_value=True)
    mock_remove = mocker.patch("os.remove")

    await file_system_plugin.dequeue_message('channel', 'thread', 'message_id')
    
    # Vérification de l'appel à la suppression
    mock_remove.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'messages_queue', 'channel_thread_message_id.txt'))

@pytest.mark.asyncio
async def test_has_older_messages_no_old_message(file_system_plugin, mocker):
    mocker.patch("time.time", return_value=1000000)
    mocker.patch("os.listdir", return_value=["channel_thread_1000.txt", "channel_thread_1001.txt"])
    mocker.patch("os.path.exists", return_value=True)

    # Configurer le TTL pour simuler un message récent
    file_system_plugin.global_manager.bot_config.MESSAGE_QUEUING_TTL = 100
    
    result = await file_system_plugin.has_older_messages('channel', 'thread')

    # Vérification qu'aucun message n'est supprimé
    assert result is False
