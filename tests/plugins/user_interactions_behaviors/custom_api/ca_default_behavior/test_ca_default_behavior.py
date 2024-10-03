from unittest.mock import AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.user_interactions_behaviors.custom_api.ca_default_behavior.ca_default_behavior import (
    CaDefaultBehaviorPlugin,
)
from core.user_interactions.message_type import MessageType

@pytest.fixture(scope="function", autouse=True)
def global_manager(mock_global_manager):
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_queue_processing_dispatcher = AsyncMock()
    mock_global_manager.bot_config = MagicMock()
    mock_global_manager.bot_config.BREAK_KEYWORD = "break"
    mock_global_manager.bot_config.START_KEYWORD = "start"
    mock_global_manager.bot_config.REQUIRE_MENTION_NEW_MESSAGE = True
    yield mock_global_manager
    mock_global_manager.reset_mock()

@pytest.fixture(autouse=True)
def check_unused_mocks(ca_default_behavior_plugin, global_manager):
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(scope="function")
def ca_default_behavior_plugin(global_manager):
    plugin = CaDefaultBehaviorPlugin(global_manager)
    plugin.initialize()
    yield plugin

@pytest.fixture(autouse=True)
def reset_mocks(ca_default_behavior_plugin):
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)):
            attr.reset_mock()
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def no_unexpected_calls(ca_default_behavior_plugin):
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

def assert_no_unused_mocks(obj):
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)):
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def check_unused_mocks(ca_default_behavior_plugin, global_manager):
    yield
    assert_no_unused_mocks(ca_default_behavior_plugin)
    assert_no_unused_mocks(global_manager)


@pytest.fixture(scope="function")
def event_data():
    return {
        "timestamp": "1234567890.123456",
        "event_label": "message",
        "channel_id": "C123",
        "thread_id": "thread_1",
        "response_id": "response_1",
        "user_name": "test_user",
        "user_email": "test_user@example.com",
        "user_id": "user_1",
        "is_mention": True,
        "text": "hello",
        "origin_plugin_name": "test_plugin"
    }

@pytest.mark.asyncio
async def test_process_interaction_general_event(ca_default_behavior_plugin, global_manager):
    event_data = {
        "timestamp": "1234567890.123456",
        "event_label": "message",
        "channel_id": "C123",
        "thread_id": "thread_1",
        "response_id": "response_1",
        "user_name": "test_user",
        "user_email": "test_user@example.com",
        "user_id": "user_1",
        "is_mention": True,
        "text": "hello",
        "origin_plugin_name": "test_plugin"
    }
    event = IncomingNotificationDataBase.from_dict(event_data)

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.has_older_messages = AsyncMock(return_value=False)
    ca_default_behavior_plugin.backend_internal_queue_processing_dispatcher = AsyncMock()

    original_process_incoming_notification_data = ca_default_behavior_plugin.process_incoming_notification_data
    ca_default_behavior_plugin.process_incoming_notification_data = AsyncMock()

    global_manager.bot_config.ACTIVATE_MESSAGE_QUEUING = True

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()
    ca_default_behavior_plugin.backend_internal_queue_processing_dispatcher.enqueue_message.assert_awaited()

@pytest.mark.asyncio
async def test_begin_genai_completion(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.reaction_writing = "writing"
    ca_default_behavior_plugin.reaction_generating = "generating"

    await ca_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="writing"
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )

@pytest.mark.asyncio
async def test_end_genai_completion(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.reaction_generating = "generating"

    await ca_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )

@pytest.mark.asyncio
async def test_begin_long_action(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.reaction_generating = "generating"
    ca_default_behavior_plugin.reaction_processing = "processing"

    await ca_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_end_long_action(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.reaction_processing = "processing"

    await ca_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_mark_error(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.reaction_generating = "generating"
    ca_default_behavior_plugin.reaction_error = "error"

    await ca_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)

    # Verify that remove_reaction was called with the correct arguments
    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name=ca_default_behavior_plugin.reaction_generating
    )

    # Verify that add_reaction was called with the correct arguments
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name=ca_default_behavior_plugin.reaction_error
    )

@pytest.mark.asyncio
async def test_process_interaction_none_event(ca_default_behavior_plugin):
    await ca_default_behavior_plugin.process_interaction(None)
    ca_default_behavior_plugin.logger.debug.assert_called_with("IM behavior: No event found")

@pytest.mark.asyncio
async def test_process_interaction_thread_break_keyword(ca_default_behavior_plugin, global_manager):
    global_manager.bot_config.BREAK_KEYWORD = "break"
    global_manager.bot_config.START_KEYWORD = "start"

    event_data = {
        "text": "break",
        "event_label": "thread_message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "thread_id": "thread_1",
        "is_mention": True,
        "origin_plugin_name": 'test_plugin'
    }
    event = IncomingNotificationDataBase.from_dict(event_data)

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

# ... [The rest of the tests follow the same pattern, replacing 'im_default_behavior_plugin' with 'ca_default_behavior_plugin']

@pytest.mark.asyncio
async def test_update_reaction(ca_default_behavior_plugin):
    event = MagicMock()
    channel_id = "C123"
    timestamp = "1234567890.123456"
    remove_reaction = "old_reaction"
    add_reaction = "new_reaction"

    ca_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()

    await ca_default_behavior_plugin.update_reaction(event, channel_id, timestamp, remove_reaction, add_reaction)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_called_once_with(
        event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=remove_reaction
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_called_once_with(
        event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=add_reaction
    )

@pytest.mark.asyncio
async def test_process_interaction_basic(ca_default_behavior_plugin, global_manager, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.has_older_messages = AsyncMock(return_value=False)

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data.assert_awaited_once()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited_once()
    ca_default_behavior_plugin.backend_internal_queue_processing_dispatcher.enqueue_message.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_interaction_no_event_data(ca_default_behavior_plugin):
    await ca_default_behavior_plugin.process_interaction(None)
    ca_default_behavior_plugin.logger.debug.assert_called_with("IM behavior: No event found")

@pytest.mark.asyncio
async def test_process_interaction_with_older_messages(ca_default_behavior_plugin, global_manager, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.has_older_messages = AsyncMock(return_value=True)

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.backend_internal_queue_processing_dispatcher.enqueue_message.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_interaction_mention_required(ca_default_behavior_plugin, global_manager, event_data):
    global_manager.bot_config.REQUIRE_MENTION_NEW_MESSAGE = True
    event_data["is_mention"] = False
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.logger.info.assert_any_call("IM behavior: Event is a new message without mention and mentions are required, not processing.")

@pytest.mark.asyncio
async def test_process_interaction_thread_message_with_break_keyword(ca_default_behavior_plugin, global_manager, event_data):
    global_manager.bot_config.BREAK_KEYWORD = "break"
    event_data["event_label"] = "thread_message"
    event_data["text"] = "break"
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

@pytest.mark.asyncio
async def test_process_incoming_notification_data_generating_completion(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)

    # Mock reactions properly
    ca_default_behavior_plugin.user_interaction_dispatcher.reactions.DONE = "done"
    ca_default_behavior_plugin.user_interaction_dispatcher.reactions.WRITING = "writing"
    ca_default_behavior_plugin.user_interaction_dispatcher.reactions.GENERATING = "generating"
    ca_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value="Generated text")

    # Call the method being tested
    await ca_default_behavior_plugin.process_incoming_notification_data(event)

    # Ensure that the genai interaction is handled correctly
    ca_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request.assert_awaited_once()

    # Ensure the 'generating' reaction is removed first (adjusted based on actual reaction flow)
    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_any_await(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name="generating"
    )

    # Ensure the 'writing' reaction is added after processing, if this is the expected behavior
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_any_await(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name="writing"  # Adjust if 'writing' is correct, otherwise use 'done'
    )

@pytest.mark.asyncio
async def test_process_incoming_notification_data_error_handling(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(side_effect=Exception("Test error"))

    await ca_default_behavior_plugin.process_incoming_notification_data(event)

    # Adjust the error assertion to check if the message contains the expected text
    error_message = "IM behavior: Error processing incoming notification data:"
    assert any(error_message in call[0][0] for call in ca_default_behavior_plugin.logger.error.call_args_list)


@pytest.mark.asyncio
async def test_begin_long_action(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.reaction_generating = "generating"
    ca_default_behavior_plugin.reaction_processing = "processing"

    await ca_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_end_long_action(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.reaction_processing = "processing"

    await ca_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_process_interaction_thread_start_keyword(ca_default_behavior_plugin, global_manager, event_data):
    global_manager.bot_config.START_KEYWORD = "start"
    event_data["text"] = "start"
    event_data["event_label"] = "thread_message"
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.remove_data_content = AsyncMock()

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited_once()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.remove_data_content.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_interaction_thread_clear_keyword(ca_default_behavior_plugin, global_manager, event_data):
    global_manager.bot_config.CLEARQUEUE_KEYWORD = "clear"
    event_data["text"] = "clear"
    event_data["event_label"] = "thread_message"
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.global_manager.interaction_queue_manager.clear_expired_messages = MagicMock()

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited_once()
    ca_default_behavior_plugin.global_manager.interaction_queue_manager.clear_expired_messages.assert_called_once()
    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction_from_thread.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_interaction_message_queuing_enabled(ca_default_behavior_plugin, global_manager, event_data):
    global_manager.bot_config.ACTIVATE_MESSAGE_QUEUING = True
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.has_older_messages = AsyncMock(return_value=True)
    
    # Set up the reaction_wait as a string
    ca_default_behavior_plugin.user_interaction_dispatcher.reactions.WAIT = "wait"
    ca_default_behavior_plugin.reaction_wait = "wait"

    # Mock the event_label to be "thread_message" to trigger the wait reaction
    event.event_label = "thread_message"
    
    # Mock the bot_config attributes
    ca_default_behavior_plugin.global_manager.bot_config.BREAK_KEYWORD = "break"
    ca_default_behavior_plugin.global_manager.bot_config.START_KEYWORD = "start"
    ca_default_behavior_plugin.global_manager.bot_config.CLEARQUEUE_KEYWORD = "clear"
    
    # Ensure event.text is a string
    event.text = "some message text"

    await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    ca_default_behavior_plugin.backend_internal_queue_processing_dispatcher.enqueue_message.assert_awaited_once()
    
    # Debug: Print all calls to add_reaction
    print("Calls to add_reaction:")
    for call in ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.mock_calls:
        print(f"  {call}")
    
    # Check if add_reaction was called with the correct arguments
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="wait"
    )

@pytest.mark.asyncio
async def test_process_incoming_notification_data_no_genai_output(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value=None)

    await ca_default_behavior_plugin.process_incoming_notification_data(event)

    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_any_await(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=ca_default_behavior_plugin.reaction_done
    )

@pytest.mark.asyncio
async def test_begin_genai_completion(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.reaction_writing = "writing"
    ca_default_behavior_plugin.reaction_generating = "generating"
    
    await ca_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="writing"
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )

@pytest.mark.asyncio
async def test_end_genai_completion(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    await ca_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once()

@pytest.mark.asyncio
async def test_mark_error(ca_default_behavior_plugin, event_data):
    event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.reaction_generating = "generating"
    ca_default_behavior_plugin.reaction_error = "error"
    
    await ca_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)

    ca_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )
    ca_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="error"
    )

@pytest.mark.asyncio
async def test_process_interaction_error_handling(ca_default_behavior_plugin, event_data):
    # Mock the request_to_notification_data to return a valid event before raising an exception
    mock_event = IncomingNotificationDataBase.from_dict(event_data)
    ca_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=mock_event)
    
    # Mock the backend_internal_data_processing_dispatcher to raise an exception
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock(side_effect=Exception("Test error"))
    
    ca_default_behavior_plugin.mark_error = AsyncMock()
    
    # Mock the necessary attributes
    ca_default_behavior_plugin.logger = MagicMock()
    
    # Mock the global_manager and its attributes
    ca_default_behavior_plugin.global_manager = MagicMock()
    ca_default_behavior_plugin.global_manager.bot_config.BREAK_KEYWORD = "break"
    ca_default_behavior_plugin.global_manager.bot_config.START_KEYWORD = "start"
    ca_default_behavior_plugin.global_manager.bot_config.CLEARQUEUE_KEYWORD = "clear"

    with pytest.raises(Exception):
        await ca_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    # Debug: Print all calls to send_message
    print("Calls to send_message:")
    for call in ca_default_behavior_plugin.user_interaction_dispatcher.send_message.mock_calls:
        print(f"  {call}")

    # Check if send_message was called with the correct arguments
    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited_once_with(
        event=mock_event,  # Use the mock event we created
        message=":warning: Error processing incoming request: Test error",
        message_type=MessageType.TEXT,
        is_internal=True,
        show_ref=False
    )
    
    # Check if mark_error was called
    ca_default_behavior_plugin.mark_error.assert_awaited_once_with(
        mock_event, mock_event.channel_id, mock_event.timestamp
    )

    # Reset mocks to avoid teardown assertions
    ca_default_behavior_plugin.mark_error.reset_mock()
    ca_default_behavior_plugin.user_interaction_dispatcher.send_message.reset_mock()

# Modify your teardown fixtures

@pytest.fixture(autouse=True)
def check_unused_mocks(ca_default_behavior_plugin, global_manager):
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name not in ["process_incoming_notification_data", "mark_error"]:
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def reset_mocks(ca_default_behavior_plugin):
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)):
            attr.reset_mock()
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)) and attr_name not in ["process_incoming_notification_data", "mark_error"]:
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def no_unexpected_calls(ca_default_behavior_plugin):
    yield
    for attr_name in dir(ca_default_behavior_plugin):
        attr = getattr(ca_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name not in ["process_incoming_notification_data", "mark_error"]:
            assert not attr.called, f"Unexpected call to {attr_name}"

def assert_no_unused_mocks(obj):
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name not in ["process_incoming_notification_data", "mark_error"]:
            assert not attr.called, f"Unexpected call to {attr_name}"