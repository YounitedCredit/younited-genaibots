import os
from unittest.mock import AsyncMock, mock_open, patch
import json
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

@pytest.mark.asyncio
async def test_append_data(file_system_plugin):
    m = mock_open()
    with patch("builtins.open", m):
        file_system_plugin.append_data('container', 'file', 'data')
        m.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'), 'a')
        m().write.assert_called_once_with('data')

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