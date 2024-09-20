from unittest.mock import AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)

def test_initialize_with_no_plugins(mock_user_interactions_dispatcher):
    mock_user_interactions_dispatcher.logger = MagicMock()
    mock_user_interactions_dispatcher.initialize([])
    mock_user_interactions_dispatcher.logger.error.assert_called_with("No plugins provided for UserInteractionsDispatcher")

def test_initialize_with_plugins(mock_user_interactions_dispatcher, mock_global_manager):
    mock_user_interactions_dispatcher.logger = MagicMock()
    mock_plugin = MagicMock(spec=UserInteractionsPluginBase)
    mock_plugin.plugin_name = "test_plugin"

    # Initialiser les plugins en tant que liste
    plugins_list = [mock_plugin]
    mock_user_interactions_dispatcher.initialize(plugins_list)

    # Vérifier que le plugin est correctement initialisé
    assert mock_user_interactions_dispatcher.plugins == plugins_list
    assert mock_user_interactions_dispatcher.plugins[0] == mock_plugin
    assert mock_user_interactions_dispatcher.plugins[0].plugin_name == "test_plugin"


@pytest.mark.asyncio
async def test_send_message(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    await mock_user_interactions_dispatcher.send_message("test_message", mock_event)
    mock_user_interactions_plugin.send_message.assert_awaited_with(
        message="test_message",
        event=mock_event,
        message_type=MessageType.TEXT,  # Corrected this line
        title=None,
        is_internal=False,
        show_ref=False
    )

@pytest.mark.asyncio
async def test_upload_file(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    await mock_user_interactions_dispatcher.upload_file(mock_event, "file_content", "filename", "title")
    mock_user_interactions_plugin.upload_file.assert_awaited_with(event=mock_event, file_content="file_content", filename="filename", title="title", is_internal=False)

@pytest.mark.asyncio
async def test_add_reaction(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    await mock_user_interactions_dispatcher.add_reaction(event=mock_event, channel_id="channel_id", timestamp="timestamp", reaction_name="reaction_name")
    mock_user_interactions_plugin.add_reaction.assert_awaited_with(event=mock_event, channel_id="channel_id", timestamp="timestamp", reaction_name="reaction_name")

@pytest.mark.asyncio
async def test_remove_reaction(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    await mock_user_interactions_dispatcher.remove_reaction(mock_event, "channel_id", "timestamp", "reaction_name")
    mock_user_interactions_plugin.remove_reaction.assert_awaited_with(channel_id="channel_id", timestamp="timestamp", reaction_name="reaction_name")

@pytest.mark.asyncio
async def test_request_to_notification_data(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    event_data = MagicMock()

    await mock_user_interactions_dispatcher.request_to_notification_data(event_data)
    mock_user_interactions_plugin.request_to_notification_data.assert_awaited_with(event_data)

@pytest.mark.asyncio
async def test_process_event_data(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Set up the mock plugins in the dispatcher
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin

    # Mock the async method process_event_data
    mock_user_interactions_plugin.process_event_data = AsyncMock()

    # Create a mock event
    event = MagicMock(spec=IncomingNotificationDataBase)
    event.origin_plugin_name = mock_user_interactions_plugin.plugin_name

    headers = {"header": "value"}
    raw_body_str = "raw body"

    # Call the process_event_data method
    await mock_user_interactions_dispatcher.process_event_data(event, headers, raw_body_str)

    # Assert that the process_event_data method was awaited with the correct arguments
    mock_user_interactions_plugin.process_event_data.assert_awaited_with(
        event_data=event, headers=headers, raw_body_str=raw_body_str
    )
