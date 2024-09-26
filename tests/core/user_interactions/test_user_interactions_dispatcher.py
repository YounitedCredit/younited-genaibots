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

    await mock_user_interactions_dispatcher.remove_reaction(event=mock_event, channel_id="channel_id", timestamp="timestamp", reaction_name="reaction_name")
    mock_user_interactions_plugin.remove_reaction.assert_awaited_with(event=mock_event, channel_id="channel_id", timestamp="timestamp", reaction_name="reaction_name")

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

def setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    """Helper to set up mock plugins for tests"""
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_user_interactions_plugin.plugin_name = "test_plugin"
    mock_user_interactions_plugin.route_path = "/test_route"
    mock_user_interactions_plugin.route_methods = ["GET", "POST"]
    mock_user_interactions_plugin.reactions = MagicMock()
    mock_user_interactions_plugin.validate_request = AsyncMock(return_value=True)
    mock_user_interactions_plugin.handle_request = AsyncMock(return_value="handled")
    mock_user_interactions_plugin.get_bot_id = MagicMock(return_value="test_bot_id")
    mock_user_interactions_plugin.fetch_conversation_history = AsyncMock(return_value=["message1", "message2"])
    mock_user_interactions_plugin.remove_reaction_from_thread = AsyncMock()


def test_plugin_name_property(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    assert mock_user_interactions_dispatcher.plugin_name == "test_plugin"


def test_route_path_property(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    assert mock_user_interactions_dispatcher.route_path == "/test_route"


def test_route_methods_property(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    assert mock_user_interactions_dispatcher.route_methods == ["GET", "POST"]


def test_reactions_property(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    assert mock_user_interactions_dispatcher.reactions is mock_user_interactions_plugin.reactions


def test_reactions_setter(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    mock_reaction = MagicMock()
    mock_user_interactions_dispatcher.reactions = mock_reaction
    assert mock_user_interactions_plugin.reactions == mock_reaction


@pytest.mark.asyncio
async def test_validate_request(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    mock_request = MagicMock()

    result = await mock_user_interactions_dispatcher.validate_request(mock_request)
    assert result is True
    mock_user_interactions_plugin.validate_request.assert_awaited_with(mock_request)


@pytest.mark.asyncio
async def test_handle_request(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    mock_request = MagicMock()

    result = await mock_user_interactions_dispatcher.handle_request(mock_request)
    assert result == "handled"
    mock_user_interactions_plugin.handle_request.assert_awaited_with(mock_request)


@pytest.mark.asyncio
async def test_remove_reaction_from_thread(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)

    await mock_user_interactions_dispatcher.remove_reaction_from_thread("channel_id", "thread_id", "reaction_name")
    mock_user_interactions_plugin.remove_reaction_from_thread.assert_awaited_with(
        "channel_id", "thread_id", "reaction_name"
    )

@pytest.mark.asyncio
async def test_fetch_conversation_history(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    result = await mock_user_interactions_dispatcher.fetch_conversation_history(mock_event, "channel_id", "thread_id")
    assert result == ["message1", "message2"]
    
    # Correction : utiliser les arguments avec des mots-clés (kwargs) comme dans l'appel réel
    mock_user_interactions_plugin.fetch_conversation_history.assert_awaited_with(
        event=mock_event, 
        channel_id="channel_id", 
        thread_id="thread_id"
    )

def test_get_bot_id(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    setup_mock_plugins(mock_user_interactions_dispatcher, mock_user_interactions_plugin)

    bot_id = mock_user_interactions_dispatcher.get_bot_id()
    assert bot_id == "test_bot_id"
    mock_user_interactions_plugin.get_bot_id.assert_called_once()