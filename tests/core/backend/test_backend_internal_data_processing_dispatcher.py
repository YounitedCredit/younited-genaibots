# tests/core/backend/test_backend_internal_data_processing_dispatcher.py

from unittest.mock import MagicMock

import pytest

from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.backend.internal_data_processing_base import InternalDataProcessingBase


@pytest.fixture
def dispatcher(mock_global_manager):
    return BackendInternalDataProcessingDispatcher(mock_global_manager)

@pytest.fixture
def mock_plugin():
    # Crée un plugin fictif avec un nom correct
    plugin = MagicMock(spec=InternalDataProcessingBase)
    plugin.plugin_name = 'mock_plugin' 
    return plugin


def test_initialize(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    assert dispatcher.plugins == [mock_plugin]
    assert dispatcher.default_plugin_name == dispatcher.global_manager.bot_config.INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME

def test_initialize_no_plugins(dispatcher):
    dispatcher.initialize([])
    dispatcher.logger.error.assert_called_with("No plugins provided for BackendInternalDataProcessingDispatcher")

def test_get_plugin(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin('mock_plugin')
    assert plugin == mock_plugin

def test_property_plugins(dispatcher, mock_plugin):
    dispatcher.plugins = [mock_plugin]
    assert dispatcher.plugins == [mock_plugin]

def test_property_plugin_name(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    assert dispatcher.plugin_name == 'mock_plugin'

def test_property_sessions(dispatcher, mock_plugin):
    mock_plugin.sessions = 'mock_sessions'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    assert dispatcher.sessions == 'mock_sessions'

@pytest.mark.asyncio
async def test_append_data(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    dispatcher.append_data('container_name', 'data_id', 'data')
    mock_plugin.append_data.assert_called_with('container_name', 'data_id', 'data')

@pytest.mark.asyncio
async def test_read_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.read_data_content('container', 'file')
    mock_plugin.read_data_content.assert_called_with(data_container='container', data_file='file')

@pytest.mark.asyncio
async def test_write_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.write_data_content('container', 'file', 'data')
    mock_plugin.write_data_content.assert_called_with(data_container='container', data_file='file', data='data')

@pytest.mark.asyncio
async def test_update_pricing(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.update_pricing('container', 'file', 'pricing_data')
    mock_plugin.update_pricing.assert_called_with(container_name='container', datafile_name='file', pricing_data='pricing_data')

@pytest.mark.asyncio
async def test_update_prompt_system_message(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.update_prompt_system_message('channel', 'thread', 'message')
    mock_plugin.update_prompt_system_message.assert_called_with(channel_id='channel', thread_id='thread', message='message')

@pytest.mark.asyncio
async def test_update_session(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.update_session('container', 'file', 'role', 'content')
    mock_plugin.update_session.assert_called_with(data_container='container', data_file='file', role='role', content='content')

@pytest.mark.asyncio
async def test_remove_data_content(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.remove_data_content('container', 'file')
    mock_plugin.remove_data_content.assert_called_with(data_container='container', data_file='file')

@pytest.mark.asyncio
async def test_list_container_files(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin  # Définir manuellement le default_plugin
    await dispatcher.list_container_files('container')
    mock_plugin.list_container_files.assert_called_with(container_name='container')

def test_property_feedbacks(dispatcher, mock_plugin):
    mock_plugin.feedbacks = 'mock_feedbacks'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.feedbacks == 'mock_feedbacks'

def test_property_concatenate(dispatcher, mock_plugin):
    mock_plugin.concatenate = 'mock_concatenate'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.concatenate == 'mock_concatenate'

def test_property_prompts(dispatcher, mock_plugin):
    mock_plugin.prompts = 'mock_prompts'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.prompts == 'mock_prompts'

def test_property_costs(dispatcher, mock_plugin):
    mock_plugin.costs = 'mock_costs'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.costs == 'mock_costs'

def test_property_processing(dispatcher, mock_plugin):
    mock_plugin.processing = 'mock_processing'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.processing == 'mock_processing'

def test_property_abort(dispatcher, mock_plugin):
    mock_plugin.abort = 'mock_abort'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.abort == 'mock_abort'

def test_property_vectors(dispatcher, mock_plugin):
    mock_plugin.vectors = 'mock_vectors'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.vectors == 'mock_vectors'

def test_property_subprompts(dispatcher, mock_plugin):
    mock_plugin.subprompts = 'mock_subprompts'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.subprompts == 'mock_subprompts'

def test_property_custom_actions(dispatcher, mock_plugin):
    mock_plugin.custom_actions = 'mock_custom_actions'
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = mock_plugin
    assert dispatcher.custom_actions == 'mock_custom_actions'

def test_get_plugin_not_found_returns_default(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    
    # Manually setting the default plugin
    dispatcher.default_plugin = mock_plugin

    # Now request a non-existent plugin
    plugin = dispatcher.get_plugin('non_existent_plugin')

    # Assert that the default plugin is returned
    dispatcher.logger.error.assert_called_with("BackendInternalDataProcessingDispatcher: Plugin 'non_existent_plugin' not found, returning default plugin")
    
    # Assert the default plugin is returned (which is 'mock_plugin' in this case)
    assert plugin == mock_plugin
