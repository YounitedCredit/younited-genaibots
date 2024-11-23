import json
import os
from unittest.mock import AsyncMock, call, mock_open, patch

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
        "FILE_SYSTEM_MESSAGES_QUEUE_CONTAINER": "messages_queue",
        "FILE_SYSTEM_CHAINOFTHOUGHTS_CONTAINER": "chainofthoughts"
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

def test_init_shares_permission_error(file_system_plugin):
    with patch("os.makedirs", side_effect=OSError("Permission denied")), pytest.raises(OSError):
        file_system_plugin.init_shares()

async def read_data_content(self, data_container, data_file):
    self.logger.debug(f"Reading data content from {data_file} in {data_container}")
    file_path = os.path.join(self.root_directory, data_container, data_file)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                data = file.read()
            self.logger.debug("Data successfully read")
            return data
        except UnicodeDecodeError as e:
            self.logger.error(f"Failed to read file due to encoding error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to read file: {str(e)}")
            return None
    else:
        self.logger.debug(f"File not found: {data_file}")
        return None
    
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
        m.assert_called_once_with(
            os.path.join(file_system_plugin.root_directory, 'container', 'file'),
            'w', encoding='utf-8'
        )

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

async def remove_data(self, container_name: str, datafile_name: str, data: str):
    file_path = os.path.join(self.root_directory, container_name, datafile_name)
    try:
        data_lower = data.lower()
        existing_content = await self.read_data_content(container_name, datafile_name)
        if existing_content is None:
            return
            
        if data_lower in existing_content.lower():
            new_content = '\n'.join([line for line in existing_content.split('\n') 
                                   if data_lower not in line.lower()])
            if new_content == "":
                new_content = " "
            await self.remove_data_content(data_container=container_name, data_file=datafile_name)
            await self.write_data_content(data_container=container_name, data_file=datafile_name, data=new_content)
            self.logger.info(f"Data successfully removed from {file_path}.")
    except IOError as e:
        self.logger.error(f"Failed to remove data from file {file_path}: {e}")
        raise e

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
        m.assert_called_once_with(
            os.path.join(file_system_plugin.root_directory, 'container', 'file'),
            'w', encoding='utf-8'
        )

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

def test_chainofthoughts_property(file_system_plugin):
    assert file_system_plugin.chainofthoughts == file_system_plugin.chainofthoughts_container

def test_initialize_with_missing_config(mock_global_manager):
    # On doit modifier la config avant d'initialiser le plugin
    mock_global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING = {}
    with pytest.raises(KeyError):
        FileSystemPlugin(global_manager=mock_global_manager).initialize()

@pytest.mark.asyncio
async def test_read_data_content_general_exception(file_system_plugin):
    m = mock_open()
    m.side_effect = Exception("General error")
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        content = await file_system_plugin.read_data_content('container', 'file')
        assert content is None

@pytest.mark.asyncio
async def test_write_data_content_with_traceback(file_system_plugin):
    with patch("builtins.open", side_effect=Exception("Write error")), \
         patch("traceback.format_exc", return_value="Error traceback"):
        await file_system_plugin.write_data_content('container', 'file', 'data')
        assert file_system_plugin.logger.error.called

@pytest.mark.asyncio
async def test_update_pricing_invalid_json(file_system_plugin):
    m = mock_open(read_data='invalid json')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        pricing_data = PricingData(total_tokens=50, prompt_tokens=25, completion_tokens=25,
                                 total_cost=0.5, input_cost=0.25, output_cost=0.25)
        result = await file_system_plugin.update_pricing("container", "file", pricing_data)
        assert result.total_tokens == 50

@pytest.mark.asyncio
async def test_update_prompt_system_message_invalid_json(file_system_plugin):
    m = mock_open(read_data='invalid json')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        await file_system_plugin.update_prompt_system_message("channel", "thread", "new message")
        assert file_system_plugin.logger.error.called

@pytest.mark.asyncio
async def test_update_prompt_system_message_no_system_role(file_system_plugin):
    m = mock_open(read_data='[{"role": "user", "content": "hello"}]')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True):
        await file_system_plugin.update_prompt_system_message("channel", "thread", "new message")
        assert file_system_plugin.logger.warning.called

@pytest.mark.asyncio
async def test_clear_container_with_subdirectories(file_system_plugin):
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=["file1.txt", "subdir"]), \
         patch("os.path.isfile", side_effect=[True, False]), \
         patch("os.path.isdir", side_effect=[True, True]), \
         patch("os.remove") as mock_remove, \
         patch("os.rmdir") as mock_rmdir:
        await file_system_plugin.clear_container("test_container")
        assert mock_remove.called
        assert mock_rmdir.called

@pytest.mark.asyncio
async def test_clear_container_error_handling(file_system_plugin):
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", side_effect=Exception("Permission denied")), \
         pytest.raises(Exception):
        await file_system_plugin.clear_container("test_container")

@pytest.mark.asyncio
async def test_file_exists(file_system_plugin):
    with patch("os.path.exists", return_value=True):
        result = await file_system_plugin.file_exists("container", "file.txt")
        assert result is True

    with patch("os.path.exists", return_value=False):
        result = await file_system_plugin.file_exists("container", "nonexistent.txt")
        assert result is False

def test_clear_container_sync_with_errors(file_system_plugin):
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", side_effect=Exception("Permission denied")), \
         pytest.raises(Exception):
        file_system_plugin.clear_container_sync("test_container")

def test_create_container_sync_with_errors(file_system_plugin):
    with patch("os.makedirs", side_effect=OSError("Permission denied")), \
         pytest.raises(OSError):
        file_system_plugin.create_container_sync("test_container")

# Test de la méthode remove_data avec différents scénarios
@pytest.mark.asyncio
async def test_remove_data_with_empty_content(file_system_plugin):
    with patch.object(file_system_plugin, "read_data_content", return_value="data"), \
         patch.object(file_system_plugin, "remove_data_content") as mock_remove, \
         patch.object(file_system_plugin, "write_data_content") as mock_write:
        await file_system_plugin.remove_data("container", "file", "data")
        mock_remove.assert_called_once()
        mock_write.assert_called_once_with(data_container="container", data_file="file", data=" ")

@pytest.mark.asyncio
async def test_remove_data_with_none_content(file_system_plugin):
    with patch.object(file_system_plugin, "read_data_content", return_value=None):
        await file_system_plugin.remove_data("container", "file", "data")