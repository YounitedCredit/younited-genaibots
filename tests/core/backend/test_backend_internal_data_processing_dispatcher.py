# tests/core/backend/test_backend_internal_data_processing_dispatcher.py

from unittest.mock import MagicMock

import pytest

from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.backend.internal_data_processing_base import InternalDataProcessingBase


@pytest.fixture
def mock_global_manager():
    global_manager = MagicMock()
    global_manager.logger = MagicMock()
    return global_manager

@pytest.fixture
def dispatcher(mock_global_manager):
    return BackendInternalDataProcessingDispatcher(mock_global_manager)

@pytest.fixture
def mock_plugin():
    plugin = MagicMock(spec=InternalDataProcessingBase)
    plugin.plugin_name = 'mock_plugin'
    return plugin

def test_initialize(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    assert dispatcher.plugins == [mock_plugin]
    assert dispatcher.default_plugin == mock_plugin
    assert dispatcher.default_plugin_name == 'mock_plugin'

def test_initialize_no_plugins(dispatcher):
    dispatcher.initialize([])
    dispatcher.logger.error.assert_called_with("No plugins provided for BackendInternalDataProcessingDispatcher")

def test_get_plugin(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin('mock_plugin')
    assert plugin == mock_plugin

def test_get_plugin_not_found(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin('non_existent_plugin')
    dispatcher.logger.error.assert_called_with("BackendInternalDataProcessingDispatcher: Plugin 'non_existent_plugin' not found, returning default plugin")
    assert plugin == mock_plugin

def test_get_plugin_default(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin()
    assert plugin == mock_plugin

def test_property_plugins(dispatcher, mock_plugin):
    dispatcher.plugins = [mock_plugin]
    assert dispatcher.plugins == [mock_plugin]

def test_property_plugin_name(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    assert dispatcher.plugin_name == 'mock_plugin'

def test_property_sessions(dispatcher, mock_plugin):
    mock_plugin.sessions = 'mock_sessions'
    dispatcher.initialize([mock_plugin])
    assert dispatcher.sessions == 'mock_sessions'

def test_property_messages(dispatcher, mock_plugin):
    mock_plugin.messages = 'mock_messages'
    dispatcher.initialize([mock_plugin])
    assert dispatcher.messages == 'mock_messages'

@pytest.mark.asyncio
async def test_append_data(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.append_data('container_name', 'data_id', 'data')
    mock_plugin.append_data.assert_called_with('container_name', 'data_id', 'data')

@pytest.mark.asyncio
async def test_read_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.read_data_content('container', 'file')
    mock_plugin.read_data_content.assert_called_with(data_container='container', data_file='file')

@pytest.mark.asyncio
async def test_write_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.write_data_content('container', 'file', 'data')
    mock_plugin.write_data_content.assert_called_with(data_container='container', data_file='file', data='data')

@pytest.mark.asyncio
async def test_update_pricing(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.update_pricing('container', 'file', 'pricing_data')
    mock_plugin.update_pricing.assert_called_with(container_name='container', datafile_name='file', pricing_data='pricing_data')

@pytest.mark.asyncio
async def test_update_prompt_system_message(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.update_prompt_system_message('channel', 'thread', 'message')
    mock_plugin.update_prompt_system_message.assert_called_with(channel_id='channel', thread_id='thread', message='message')

@pytest.mark.asyncio
async def test_update_session(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.update_session('container', 'file', 'role', 'content')
    mock_plugin.update_session.assert_called_with(data_container='container', data_file='file', role='role', content='content')

@pytest.mark.asyncio
async def test_remove_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.remove_data_content('container', 'file')
    mock_plugin.remove_data_content.assert_called_with(data_container='container', data_file='file')

@pytest.mark.asyncio
async def test_list_container_files(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.list_container_files('container')
    mock_plugin.list_container_files.assert_called_with(container_name='container')
