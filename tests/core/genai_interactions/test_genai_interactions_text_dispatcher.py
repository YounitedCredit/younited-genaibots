from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_input import (
    ActionInput,  # Assurez-vous d'importer ActionInput
)
from core.genai_interactions.genai_interactions_text_dispatcher import (
    GenaiInteractionsTextDispatcher,
)
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from utils.config_manager.config_model import BotConfig


@pytest.fixture
def mock_plugin():
    plugin = MagicMock(spec=GenAIInteractionsTextPluginBase)
    plugin.plugin_name = "mock_plugin"
    plugin.validate_request = MagicMock(return_value=True)
    plugin.handle_request = AsyncMock(return_value="handled_request")
    plugin.trigger_genai = AsyncMock()
    plugin.handle_action = AsyncMock(return_value="handled_action")
    plugin.load_client = AsyncMock(return_value="loaded_client")
    plugin.trigger_feedback = AsyncMock()
    plugin.generate_completion = AsyncMock(return_value="completion")
    return plugin

@pytest.fixture
def mock_bot_config():
    config = MagicMock(spec=BotConfig)
    config.GENAI_TEXT_DEFAULT_PLUGIN_NAME = "mock_plugin"
    return config

@pytest.fixture
def dispatcher(mock_global_manager, mock_bot_config, mock_plugin):
    mock_global_manager.bot_config = mock_bot_config
    dispatcher = GenaiInteractionsTextDispatcher(global_manager=mock_global_manager)
    dispatcher.initialize([mock_plugin])
    return dispatcher

@pytest.mark.asyncio
async def test_handle_request(dispatcher, mock_plugin):
    event = MagicMock(spec=IncomingNotificationDataBase)
    response = await dispatcher.handle_request(event)
    mock_plugin.handle_request.assert_awaited_once_with(event)
    assert response == "handled_request"

def test_get_plugin(dispatcher, mock_plugin):
    plugin = dispatcher.get_plugin("mock_plugin")
    assert plugin == mock_plugin

def test_initialize_without_plugins(dispatcher, mock_global_manager):
    dispatcher.initialize([])
    mock_global_manager.logger.error.assert_called_once_with("No plugins provided for GenaiInteractionsTextDispatcher")

@pytest.mark.asyncio
async def test_trigger_genai(dispatcher, mock_global_manager, mock_plugin):
    event = MagicMock(spec=IncomingNotificationDataBase)
    event.thread_id = "mock_thread_id"  # Ajoutez cet attribut
    event.channel_id = "mock_channel_id"  # Ajoutez cet attribut
    mock_global_manager.backend_internal_data_processing_dispatcher = MagicMock()
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=False)
    await dispatcher.trigger_genai(event)
    mock_plugin.trigger_genai.assert_awaited_once_with(event=event)

@pytest.mark.asyncio
async def test_handle_action(dispatcher, mock_plugin):
    action_input = MagicMock(spec=ActionInput)
    event = MagicMock(spec=IncomingNotificationDataBase)
    response = await dispatcher.handle_action(action_input, event)
    mock_plugin.handle_action.assert_awaited_once_with(action_input, event)
    assert response == "handled_action"

@pytest.mark.asyncio
async def test_load_client(dispatcher, mock_plugin):
    response = await dispatcher.load_client()
    mock_plugin.load_client.assert_awaited_once()
    assert response == "loaded_client"

@pytest.mark.asyncio
async def test_trigger_feedback(dispatcher, mock_plugin):
    event = MagicMock(spec=IncomingNotificationDataBase)
    await dispatcher.trigger_feedback(event)
    mock_plugin.trigger_feedback.assert_awaited_once_with(event=event)

@pytest.mark.asyncio
async def test_generate_completion(dispatcher, mock_plugin):
    messages = ["message1", "message2"]
    event_data = MagicMock(spec=IncomingNotificationDataBase)
    response = await dispatcher.generate_completion(messages, event_data)
    mock_plugin.generate_completion.assert_awaited_once_with(messages, event_data)
    assert response == "completion"
