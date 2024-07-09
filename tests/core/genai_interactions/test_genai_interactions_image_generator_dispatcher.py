from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_image_generator_dispatcher import (
    GenaiInteractionsImageGeneratorDispatcher,
)
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


@pytest.fixture
def mock_plugin():
    plugin = MagicMock(spec=GenAIInteractionsPluginBase)
    plugin.plugin_name = "mock_plugin"
    plugin.validate_request = AsyncMock(return_value=True)
    plugin.handle_request = AsyncMock()
    plugin.trigger_genai = AsyncMock()
    plugin.handle_action = AsyncMock(return_value=True)
    return plugin

@pytest.fixture
def dispatcher(mock_global_manager, mock_config_manager):
    # Set a default plugin name in the configuration
    mock_config_manager.config.BOT_CONFIG.GENAI_IMAGE_DEFAULT_PLUGIN_NAME = "mock_plugin"
    mock_global_manager.config_manager = mock_config_manager

    dispatcher = GenaiInteractionsImageGeneratorDispatcher(mock_global_manager)
    dispatcher.logger = MagicMock()  # Mock the logger explicitly
    return dispatcher

def test_initialize_with_no_plugins(dispatcher, caplog):
    caplog.set_level("ERROR")
    dispatcher.initialize([])
    dispatcher.logger.error.assert_called_with("No plugins provided for GenaiInteractionsImageGeneratorDispatcher")

def test_initialize_with_default_plugin(dispatcher, mock_plugin, caplog):
    caplog.set_level("INFO")
    dispatcher.initialize([mock_plugin])
    assert dispatcher.default_plugin == mock_plugin
    assert dispatcher.default_plugin_name == "mock_plugin"
    dispatcher.logger.info.assert_called_with("Setting default Genai Image plugin to <mock_plugin>")

def test_initialize_with_configured_default_plugin(dispatcher, mock_plugin, mock_config_manager, caplog):
    caplog.set_level("INFO")
    mock_config_manager.config.BOT_CONFIG.GENAI_IMAGE_DEFAULT_PLUGIN_NAME = "mock_plugin"
    dispatcher.global_manager.config_manager = mock_config_manager
    dispatcher.initialize([mock_plugin])
    assert dispatcher.default_plugin == mock_plugin
    assert dispatcher.default_plugin_name == "mock_plugin"
    dispatcher.logger.info.assert_called_with("Setting default Genai Image plugin to <mock_plugin>")

def test_get_plugin_existing(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin("mock_plugin")
    assert plugin == mock_plugin

def test_get_plugin_non_existing(dispatcher, mock_plugin, caplog):
    caplog.set_level("INFO")
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin("non_existing_plugin")
    assert plugin == mock_plugin  # Should return default plugin
    dispatcher.logger.info.assert_called_with("Setting default Genai Image plugin to <mock_plugin>")

@pytest.mark.asyncio
async def test_validate_request(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    event = MagicMock(spec=IncomingNotificationDataBase)
    result = await dispatcher.validate_request(event)
    assert result is True
    mock_plugin.validate_request.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_handle_request(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    event = MagicMock(spec=IncomingNotificationDataBase)
    await dispatcher.handle_request(event)
    mock_plugin.handle_request.assert_awaited_once_with(event)

@pytest.mark.asyncio
async def test_trigger_genai(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    event = MagicMock(spec=IncomingNotificationDataBase)
    await dispatcher.trigger_genai(event)
    mock_plugin.trigger_genai.assert_awaited_once_with(event=event)

@pytest.mark.asyncio
async def test_handle_action(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    action_input = MagicMock(spec=ActionInput)
    result = await dispatcher.handle_action(action_input)
    assert result is True
    mock_plugin.handle_action.assert_awaited_once_with(action_input)
