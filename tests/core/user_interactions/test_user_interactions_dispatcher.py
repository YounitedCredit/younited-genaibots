from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
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
    # Set up dispatcher and plugin
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin

    # Create a mock event and set required attributes
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"
    mock_event.channel_id = "test_channel"
    mock_event.thread_id = "test_thread"

    # Call the method under test
    await mock_user_interactions_dispatcher.send_message("test_message", mock_event)

    # Assert that the plugin's send_message method was called with the correct parameters
    mock_user_interactions_plugin.send_message.assert_awaited_with(
        message="test_message",
        event=mock_event,
        message_type=mock.ANY,  # If you're using a specific message type, replace this accordingly
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
    # Ensure plugins are set up as a dictionary
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    event_data = MagicMock()

    # Mock the plugin's request_to_notification_data method
    mock_user_interactions_plugin.request_to_notification_data = AsyncMock()

    # Call the method under test
    await mock_user_interactions_dispatcher.request_to_notification_data(event_data)

    # Check that the plugin's request_to_notification_data method was called
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

def test_set_default_plugin(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.set_default_plugin("test_plugin")

    # Check that the default plugin is correctly set
    assert mock_user_interactions_dispatcher.default_plugin_name == "test_plugin"
    assert mock_user_interactions_dispatcher.default_plugin == mock_user_interactions_plugin


def test_get_plugin_not_found(mock_user_interactions_dispatcher):
    mock_user_interactions_dispatcher.logger = MagicMock()

    # Ensure plugins are set up as a dictionary
    mock_user_interactions_dispatcher.plugins = {"default_category": []}

    # No default plugin is set
    mock_user_interactions_dispatcher.default_plugin = None

    # Trying to get a plugin that doesn't exist
    result = mock_user_interactions_dispatcher.get_plugin("non_existent_plugin")

    # Expecting None to be returned
    assert result is None

    # Check that the logger was called with the correct error message for no default plugin
    mock_user_interactions_dispatcher.logger.error.assert_called_with('No default plugin configured.')

@pytest.mark.asyncio
async def test_validate_request(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Ensure plugins are set up as a dictionary
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    # Mock the plugin's validate_request method
    mock_user_interactions_plugin.validate_request = AsyncMock(return_value=True)

    # Call the method under test
    result = await mock_user_interactions_dispatcher.validate_request(mock_event)

    # Check that the plugin's validate_request method was called
    mock_user_interactions_plugin.validate_request.assert_awaited_with(mock_event)
    assert result is True

@pytest.mark.asyncio
async def test_process_event_data(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"
    headers = {"header": "value"}
    raw_body_str = "raw body"

    # Mock the plugin's process_event_data method
    mock_user_interactions_plugin.process_event_data = AsyncMock()

    # Call the method under test
    await mock_user_interactions_dispatcher.process_event_data(mock_event, headers, raw_body_str)

    # Check that the plugin's process_event_data method was called with the correct parameters
    mock_user_interactions_plugin.process_event_data.assert_awaited_with(
        event_data=mock_event, headers=headers, raw_body_str=raw_body_str
    )

@pytest.mark.asyncio
async def test_send_message_with_replay(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    mock_event.origin_plugin_name = "test_plugin"

    # Mock the plugin's send_message method
    mock_user_interactions_plugin.send_message = AsyncMock()

    # Call the method with replay set to True
    await mock_user_interactions_dispatcher.send_message("test_message", mock_event, is_replayed=True)

    # Check that the plugin's send_message method was called with the correct parameters
    mock_user_interactions_plugin.send_message.assert_awaited_with(
        message="test_message",
        event=mock_event,
        message_type=mock.ANY,  # You can replace this with specific MessageType if needed
        title=None,
        is_internal=False,
        show_ref=False
    )

@pytest.mark.asyncio
async def test_remove_reaction_from_thread_replayed(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Scenario where `is_replayed` is True, process the event directly
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_user_interactions_dispatcher.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = False

    # Mock the plugin's `remove_reaction_from_thread` method
    mock_user_interactions_plugin.remove_reaction_from_thread = AsyncMock()

    # Call the method under test with `is_replayed=True`
    await mock_user_interactions_dispatcher.remove_reaction_from_thread("channel_id", "thread_id", "reaction_name", is_replayed=True)

    # Check that the plugin's `remove_reaction_from_thread` was called directly
    mock_user_interactions_plugin.remove_reaction_from_thread.assert_awaited_with("channel_id", "thread_id", "reaction_name")


@pytest.mark.asyncio
async def test_remove_reaction_from_thread_with_queue(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Scenario where `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled, and no background tasks are provided
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_user_interactions_dispatcher.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = True

    # Mock the event queue manager
    mock_user_interactions_dispatcher.event_queue_manager = AsyncMock()

    # Call the method under test with `is_replayed=False` and no background tasks
    await mock_user_interactions_dispatcher.remove_reaction_from_thread("channel_id", "thread_id", "reaction_name", is_replayed=False)

    # Check that the event was added to the queue
    mock_user_interactions_dispatcher.event_queue_manager.add_to_queue.assert_awaited_with(
        "remove_reaction_from_thread",
        {
            "channel_id": "channel_id",
            "thread_id": "thread_id",
            "reaction_name": "reaction_name",
            "plugin_name": None
        }
    )

@pytest.mark.asyncio
async def test_remove_reaction_from_thread_with_background_tasks(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Scenario where `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled, and background tasks are provided
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_user_interactions_dispatcher.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = True

    # Create a mock BackgroundTasks instance
    mock_background_tasks = MagicMock(spec=BackgroundTasks)

    # Call the method under test with `is_replayed=False` and background tasks provided
    await mock_user_interactions_dispatcher.remove_reaction_from_thread("channel_id", "thread_id", "reaction_name", is_replayed=False, background_tasks=mock_background_tasks)

    # Check that the background task was added
    mock_background_tasks.add_task.assert_called_once_with(
        mock_user_interactions_dispatcher._remove_reaction_from_thread_background,
        {
            "channel_id": "channel_id",
            "thread_id": "thread_id",
            "reaction_name": "reaction_name",
            "plugin_name": None
        }
    )

@pytest.mark.asyncio
async def test_remove_reaction_from_thread_no_queue(mock_user_interactions_dispatcher, mock_user_interactions_plugin):
    # Scenario where queuing is disabled, process the event directly using the plugin
    mock_user_interactions_dispatcher.plugins = {"default_category": [mock_user_interactions_plugin]}
    mock_user_interactions_dispatcher.default_plugin = mock_user_interactions_plugin
    mock_user_interactions_dispatcher.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = False

    # Mock the plugin's `remove_reaction_from_thread` method
    mock_user_interactions_plugin.remove_reaction_from_thread = AsyncMock()

    # Call the method under test with `is_replayed=False` and queuing disabled
    await mock_user_interactions_dispatcher.remove_reaction_from_thread("channel_id", "thread_id", "reaction_name", is_replayed=False)

    # Check that the plugin's `remove_reaction_from_thread` was called directly
    mock_user_interactions_plugin.remove_reaction_from_thread.assert_awaited_with("channel_id", "thread_id", "reaction_name")
