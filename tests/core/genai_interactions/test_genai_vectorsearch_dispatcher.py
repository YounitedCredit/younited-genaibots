from unittest import mock
from unittest.mock import MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.genai_interactions.genai_vectorsearch_dispatcher import GenaiVectorsearch
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


@pytest.fixture
def mock_plugin():
    plugin = MagicMock(spec=GenAIInteractionsPluginBase)
    plugin.plugin_name = "test_plugin"
    return plugin

@pytest.fixture
def genai_vectorsearch(mock_global_manager):
    return GenaiVectorsearch(mock_global_manager)

def test_initialize_no_plugins(genai_vectorsearch, mock_global_manager):
    genai_vectorsearch.initialize([])
    genai_vectorsearch.logger.error.assert_called_once_with("No plugins provided for GenaiVectorsearch")

def test_initialize_with_plugins(genai_vectorsearch, mock_plugin, mock_global_manager):
    mock_global_manager.bot_config.GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME = None
    genai_vectorsearch.initialize([mock_plugin])
    assert genai_vectorsearch.default_plugin == mock_plugin
    assert genai_vectorsearch.default_plugin_name == mock_plugin.plugin_name
    genai_vectorsearch.logger.info.assert_has_calls([
        mock.call("Setting Genai Vector Search default plugin to first plugin in list"),
        mock.call(f"Default plugin set to: <{mock_plugin.plugin_name}>")
    ], any_order=True)

def test_initialize_with_default_plugin(genai_vectorsearch, mock_plugin, mock_global_manager):
    mock_global_manager.bot_config.GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME = "test_plugin"
    genai_vectorsearch.initialize([mock_plugin])
    assert genai_vectorsearch.default_plugin == mock_plugin
    assert genai_vectorsearch.default_plugin_name == mock_plugin.plugin_name
    genai_vectorsearch.logger.info.assert_has_calls([
        mock.call("Setting default Genai Vector Search plugin to <test_plugin>"),
        mock.call("Default plugin set to: <test_plugin>")
    ], any_order=True)

def test_get_plugin_found(genai_vectorsearch, mock_plugin):
    genai_vectorsearch.plugins = [mock_plugin]
    plugin = genai_vectorsearch.get_plugin("test_plugin")
    assert plugin == mock_plugin

def test_get_plugin_not_found(genai_vectorsearch, mock_plugin):
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin = mock_plugin
    plugin = genai_vectorsearch.get_plugin("nonexistent_plugin")
    assert plugin == mock_plugin
    genai_vectorsearch.logger.error.assert_called_once_with("GenaiVectorsearch: Plugin 'nonexistent_plugin' not found, returning default plugin")

def test_plugin_name_property(genai_vectorsearch, mock_plugin):
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin_name = "test_plugin"
    assert genai_vectorsearch.plugin_name == "test_plugin"

def test_validate_request(genai_vectorsearch, mock_plugin):
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin_name = "test_plugin"
    genai_vectorsearch.validate_request(mock_event)
    mock_plugin.validate_request.assert_called_once_with(mock_event)

def test_handle_request(genai_vectorsearch, mock_plugin):
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin_name = "test_plugin"
    genai_vectorsearch.handle_request(mock_event)
    mock_plugin.handle_request.assert_called_once_with(mock_event)

@pytest.mark.asyncio
async def test_trigger_genai(genai_vectorsearch, mock_plugin):
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin_name = "test_plugin"
    await genai_vectorsearch.trigger_genai(mock_event)
    mock_plugin.trigger_genai.assert_called_once_with(event=mock_event)

@pytest.mark.asyncio
async def test_handle_action(genai_vectorsearch, mock_plugin):
    mock_action_input = MagicMock(spec=ActionInput)
    genai_vectorsearch.plugins = [mock_plugin]
    genai_vectorsearch.default_plugin_name = "test_plugin"
    await genai_vectorsearch.handle_action(mock_action_input)
    mock_plugin.handle_action.assert_called_once_with(mock_action_input)
