from unittest.mock import AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)


def test_initialize_with_no_plugins(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_user_interactions_behaviors_dispatcher.initialize({})
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("No plugins provided for UserInteractionsBehaviorsDispatcher")

def test_initialize_with_plugins(mock_user_interactions_behaviors_dispatcher, mock_global_manager):
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_plugin = MagicMock(spec=UserInteractionsPluginBase)
    mock_plugin.plugin_name = "test_plugin"

    # Mocking the get_plugin method to return a valid plugin when called with the default plugin name
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)

    mock_global_manager.bot_config.USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME = "test_plugin"

    plugins = {"default_category": [mock_plugin]}

    mock_user_interactions_behaviors_dispatcher.initialize(plugins)

    assert mock_user_interactions_behaviors_dispatcher.plugins == plugins
    assert mock_user_interactions_behaviors_dispatcher.default_plugin_name == "test_plugin"

@pytest.mark.asyncio
async def test_process_interaction_with_valid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_plugin.plugin_name = "valid_plugin"
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event_data = MagicMock()
    mock_event_origin = MagicMock()

    await mock_user_interactions_behaviors_dispatcher.process_interaction(mock_event_data, mock_event_origin)
    mock_plugin.process_interaction.assert_awaited_with(mock_event_data, mock_event_origin)

@pytest.mark.asyncio
async def test_process_interaction_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()

    await mock_user_interactions_behaviors_dispatcher.process_interaction(MagicMock(), MagicMock(), "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling process_interaction in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_process_incoming_notification_data_with_valid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_plugin.plugin_name = "valid_plugin"
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.process_incoming_notification_data(mock_event)
    mock_plugin.process_incoming_notification_data.assert_awaited_with(mock_event)

@pytest.mark.asyncio
async def test_process_incoming_notification_data_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()

    await mock_user_interactions_behaviors_dispatcher.process_incoming_notification_data(MagicMock(spec=IncomingNotificationDataBase), "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling process_incoming_notification_data in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_begin_genai_completion(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_genai_completion(mock_event, "channel_id", "timestamp")
    mock_plugin.begin_genai_completion.assert_awaited_with(mock_event, channel_id="channel_id", timestamp="timestamp")

@pytest.mark.asyncio
async def test_end_genai_completion(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_genai_completion(mock_event, "channel_id", "timestamp")
    mock_plugin.end_genai_completion.assert_awaited_with(mock_event, "channel_id", "timestamp")

@pytest.mark.asyncio
async def test_begin_long_action(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_long_action(mock_event, "channel_id", "timestamp")
    mock_plugin.begin_long_action.assert_awaited_with(mock_event, "channel_id", "timestamp")

@pytest.mark.asyncio
async def test_end_long_action(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_long_action(mock_event, "channel_id", "timestamp")
    mock_plugin.end_long_action.assert_awaited_with(mock_event, "channel_id", "timestamp")

@pytest.mark.asyncio
async def test_begin_wait_backend(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_wait_backend(mock_event, "channel_id", "timestamp")
    mock_plugin.begin_wait_backend.assert_awaited_with(mock_event, "channel_id", "timestamp")

@pytest.mark.asyncio
async def test_end_wait_backend(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_wait_backend(mock_event, "channel_id", "timestamp")
    mock_plugin.end_wait_backend.assert_awaited_with(mock_event, "channel_id", "timestamp")

@pytest.mark.asyncio
async def test_mark_error(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = AsyncMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.mark_error(mock_event, "channel_id", "timestamp")
    mock_plugin.mark_error.assert_awaited_with(mock_event, "channel_id", "timestamp")

def test_get_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_plugin1 = MagicMock()
    mock_plugin1.plugin_name = "plugin1"
    mock_plugin2 = MagicMock()
    mock_plugin2.plugin_name = "plugin2"
    mock_user_interactions_behaviors_dispatcher.plugins = {"category1": [mock_plugin1], "category2": [mock_plugin2]}

    assert mock_user_interactions_behaviors_dispatcher.get_plugin("plugin1") == mock_plugin1
    assert mock_user_interactions_behaviors_dispatcher.get_plugin("plugin2") == mock_plugin2
    assert mock_user_interactions_behaviors_dispatcher.get_plugin("non_existent") is None

def test_plugin_name_getter(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = MagicMock()
    mock_plugin.plugin_name = "test_plugin"
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)

    assert mock_user_interactions_behaviors_dispatcher.plugin_name == "test_plugin"

def test_plugin_name_setter(mock_user_interactions_behaviors_dispatcher):
    mock_plugin = MagicMock()
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=mock_plugin)

    mock_user_interactions_behaviors_dispatcher.plugin_name = "new_plugin_name"
    assert mock_plugin.plugin_name == "new_plugin_name"

def test_plugins_getter_setter(mock_user_interactions_behaviors_dispatcher):
    mock_plugins = [MagicMock(), MagicMock()]
    mock_user_interactions_behaviors_dispatcher.plugins = mock_plugins
    assert mock_user_interactions_behaviors_dispatcher.plugins == mock_plugins

@pytest.mark.asyncio
async def test_begin_genai_completion_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_genai_completion(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling begin_genai_completion in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_end_genai_completion_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_genai_completion(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling end_genai_completion in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_begin_long_action_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_long_action(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling begin_long_action in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_end_long_action_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_long_action(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling end_long_action in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_begin_wait_backend_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.begin_wait_backend(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling begin_wait_backend in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_end_wait_backend_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.end_wait_backend(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling end_wait_backend in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")

@pytest.mark.asyncio
async def test_mark_error_with_invalid_plugin(mock_user_interactions_behaviors_dispatcher):
    mock_user_interactions_behaviors_dispatcher.get_plugin = MagicMock(return_value=None)
    mock_user_interactions_behaviors_dispatcher.logger = MagicMock()
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    await mock_user_interactions_behaviors_dispatcher.mark_error(mock_event, "channel_id", "timestamp", "invalid_plugin")
    mock_user_interactions_behaviors_dispatcher.logger.error.assert_called_with("Error calling mark_error in UserInteractionsBehaviorDispatcher: Plugin not found: invalid_plugin")
