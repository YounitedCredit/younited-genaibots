import os
from unittest.mock import AsyncMock, mock_open, patch

import pytest

from core.backend.pricing_data import PricingData
from plugins.backend.internal_data_processing.file_system.file_system import (
    FileSystemPlugin,
)

@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "test_plugin",
        "DIRECTORY": "/test_directory",
        "SESSIONS_CONTAINER": "sessions",
        "MESSAGES_CONTAINER": "messages",
        "FEEDBACKS_CONTAINER": "feedbacks",
        "CONCATENATE_CONTAINER": "concatenate",
        "PROMPTS_CONTAINER": "prompts",
        "COSTS_CONTAINER": "costs",
        "PROCESSING_CONTAINER": "processing",
        "ABORT_CONTAINER": "abort",
        "VECTORS_CONTAINER": "vectors",
        "CUSTOM_ACTIONS_CONTAINER": "custom_actions"
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
        m.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'), 'r')

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
    assert mock_makedirs.call_count == 7

@pytest.mark.asyncio
async def test_append_data(file_system_plugin):
    m = mock_open()
    with patch("builtins.open", m):
        file_system_plugin.append_data('container', 'file', 'data')
        m.assert_called_once_with(os.path.join(file_system_plugin.root_directory, 'container', 'file'), 'a')
        m().write.assert_called_once_with('data')

@pytest.mark.asyncio
async def test_store_unmentioned_messages(file_system_plugin):
    m = mock_open(read_data='[]')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True), patch("json.dump") as mock_dump:
        message = {"content": "test"}
        await file_system_plugin.store_unmentioned_messages("channel", "thread", message)
        mock_dump.assert_called_once_with([message], m())

@pytest.mark.asyncio
async def test_retrieve_unmentioned_messages(file_system_plugin):
    m = mock_open(read_data='[{"content": "test"}]')
    with patch("builtins.open", m), patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove:
        messages = await file_system_plugin.retrieve_unmentioned_messages("channel", "thread")
        assert messages == [{"content": "test"}]
        mock_remove.assert_called_once()

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
