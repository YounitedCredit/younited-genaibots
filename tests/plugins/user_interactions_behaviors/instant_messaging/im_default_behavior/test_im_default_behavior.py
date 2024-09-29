from unittest.mock import AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.user_interactions_behaviors.instant_messaging.im_default_behavior.im_default_behavior import (
    ImDefaultBehaviorPlugin,
)


@pytest.fixture(scope="function", autouse=True)
def global_manager(mock_global_manager):
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_queue_processing_dispatcher = AsyncMock()  # Add this line
    mock_global_manager.bot_config = MagicMock()
    mock_global_manager.bot_config.BREAK_KEYWORD = "break"
    mock_global_manager.bot_config.START_KEYWORD = "start"
    mock_global_manager.bot_config.REQUIRE_MENTION_NEW_MESSAGE = True
    yield mock_global_manager
    mock_global_manager.reset_mock()

@pytest.fixture(autouse=True)
def check_unused_mocks(im_default_behavior_plugin, global_manager):
    yield
    for attr_name in dir(im_default_behavior_plugin):
        attr = getattr(im_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(scope="function")
def im_default_behavior_plugin(global_manager):
    plugin = ImDefaultBehaviorPlugin(global_manager)
    plugin.initialize()
    yield plugin

@pytest.fixture(autouse=True)
def reset_mocks(im_default_behavior_plugin):
    # Reset all mocks before each test
    for attr_name in dir(im_default_behavior_plugin):
        attr = getattr(im_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)):
            attr.reset_mock()
    yield
    # After the test, check for unexpected calls
    for attr_name in dir(im_default_behavior_plugin):
        attr = getattr(im_default_behavior_plugin, attr_name)
        if isinstance(attr, (AsyncMock, MagicMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def no_unexpected_calls(im_default_behavior_plugin):
    yield
    for attr_name in dir(im_default_behavior_plugin):
        attr = getattr(im_default_behavior_plugin, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)) and attr_name != "process_incoming_notification_data":
            assert not attr.called, f"Unexpected call to {attr_name}"

def assert_no_unused_mocks(obj):
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        if isinstance(attr, (MagicMock, AsyncMock)):
            assert not attr.called, f"Unexpected call to {attr_name}"

@pytest.fixture(autouse=True)
def check_unused_mocks(im_default_behavior_plugin, global_manager):
    yield
    assert_no_unused_mocks(im_default_behavior_plugin)
    assert_no_unused_mocks(global_manager)

@pytest.mark.asyncio
async def test_process_interaction_general_event(im_default_behavior_plugin, global_manager):
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

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.has_older_messages = AsyncMock(return_value=False)
    im_default_behavior_plugin.backend_internal_queue_processing_dispatcher = AsyncMock()

    original_process_incoming_notification_data = im_default_behavior_plugin.process_incoming_notification_data
    im_default_behavior_plugin.process_incoming_notification_data = AsyncMock()

    # Active message queuing to ensure enqueue_message is awaited
    global_manager.bot_config.ACTIVATE_MESSAGE_QUEUING = True

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    # Verify that the appropriate methods were called
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()
    im_default_behavior_plugin.backend_internal_queue_processing_dispatcher.enqueue_message.assert_awaited()


@pytest.mark.asyncio
async def test_begin_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_writing = "writing"
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="writing"
    )
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )

@pytest.mark.asyncio
async def test_end_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )

@pytest.mark.asyncio
async def test_begin_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating"
    )
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_end_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once_with(
        event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing"
    )

@pytest.mark.asyncio
async def test_mark_error(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_error = "error"

    await im_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)

    # Vérifier que update_reaction a été appelé avec les bons arguments
    im_default_behavior_plugin.update_reaction.assert_awaited_with(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        remove_reaction=im_default_behavior_plugin.reaction_generating,
        add_reaction=im_default_behavior_plugin.reaction_error
    )

@pytest.mark.asyncio
async def test_process_interaction_none_event(im_default_behavior_plugin):
    await im_default_behavior_plugin.process_interaction(None)
    im_default_behavior_plugin.logger.debug.assert_called_with("IM behavior: No event")

@pytest.mark.asyncio
async def test_process_interaction_thread_break_keyword(im_default_behavior_plugin, global_manager):
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

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    im_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

@pytest.mark.asyncio
async def test_process_interaction_break_keyword(im_default_behavior_plugin, global_manager):
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

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=IncomingNotificationDataBase.from_dict(event_data))
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    im_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

@pytest.mark.asyncio
async def test_begin_end_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_writing = "writing"
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once()
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once()

    await im_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited()

@pytest.mark.asyncio
async def test_begin_end_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once()
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once()

    await im_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited()

@pytest.mark.asyncio
async def test_begin_end_wait_backend(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.instantmessaging_plugin = AsyncMock()
    im_default_behavior_plugin.reaction_wait = "wait"

    await im_default_behavior_plugin.begin_wait_backend(event, event.channel_id, event.timestamp)
    # Comme la méthode est actuellement vide, nous vérifions simplement qu'elle ne lève pas d'exception
    assert True

    await im_default_behavior_plugin.end_wait_backend(event, event.channel_id, event.timestamp)
    # Comme la méthode est actuellement vide, nous vérifions simplement qu'elle ne lève pas d'exception
    assert True

@pytest.mark.asyncio
async def test_mark_error(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_error = "error"

    await im_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)

    # Vérifier que remove_reaction a été appelé avec la bonne réaction
    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_with(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name=im_default_behavior_plugin.reaction_generating
    )

    # Vérifier que add_reaction a été appelé avec la bonne réaction
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_with(
        event=event,
        channel_id=event.channel_id,
        timestamp=event.timestamp,
        reaction_name=im_default_behavior_plugin.reaction_error
    )

    # Afficher les appels pour le débogage
    print("Calls to remove_reaction:")
    for call in im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.call_args_list:
        print(f"Args: {call.args}, Kwargs: {call.kwargs}")

    print("Calls to add_reaction:")
    for call in im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.call_args_list:
        print(f"Args: {call.args}, Kwargs: {call.kwargs}")

@pytest.mark.asyncio
async def test_update_reaction(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()

    await im_default_behavior_plugin.update_reaction(event, event.channel_id, event.timestamp, remove_reaction="old_reaction", add_reaction="new_reaction")

    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_awaited_once()
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_interaction_start_keyword(im_default_behavior_plugin, global_manager):
    global_manager.bot_config.START_KEYWORD = "start"
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        event_label="thread_message",
        channel_id="C123",
        thread_id="thread_1",
        response_id="response_1",
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=True,
        text="start",
        origin_plugin_name="origin_plugin_name"
    )
    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event_data)
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    im_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_awaited()

@pytest.mark.asyncio
async def test_process_interaction_thread_message_no_mention(im_default_behavior_plugin, global_manager):
    global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE = True
    global_manager.bot_config.CLEARQUEUE_KEYWORD = "clear"

    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        event_label="thread_message",
        channel_id="C123",
        thread_id="thread_1",
        response_id="response_1",
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=False,
        text="Hello",
        origin_plugin_name="origin_plugin_name"
    )

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event_data)
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    im_default_behavior_plugin.user_interaction_dispatcher.send_message.assert_not_awaited()

@pytest.mark.asyncio
async def test_process_interaction_new_message_no_mention(im_default_behavior_plugin, global_manager, monkeypatch):
    monkeypatch.setattr(global_manager.bot_config, 'REQUIRE_MENTION_NEW_MESSAGE', True)
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        event_label="message",
        channel_id="C123",
        thread_id=None,
        response_id=None,
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=False,  # Not mentioning the bot
        text="Hello",
        origin_plugin_name="origin_plugin_name"
    )
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'request_to_notification_data', AsyncMock(return_value=event_data))
    plugin_mock = AsyncMock()
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'get_plugin', MagicMock(return_value=plugin_mock))

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    # Examine the method calls
    print("Number of method calls:", len(plugin_mock.method_calls))
    for i, call in enumerate(plugin_mock.method_calls):
        print(f"Call {i}:")
        print("  Method name:", call[0])
        print("  Arguments:", call[1])
        print("  Kwargs:", call[2])
        print()

    # Verify that no methods are called since the bot should not process the message
    add_reaction_calls = [call for call in plugin_mock.method_calls if call[0] == 'add_reaction']
    send_message_calls = [call for call in plugin_mock.method_calls if call[0] == 'send_message']
    remove_reaction_calls = [call for call in plugin_mock.method_calls if call[0] == 'remove_reaction']

    assert len(add_reaction_calls) == 0, "add_reaction should not be called"
    assert len(send_message_calls) == 0, "send_message should not be called"
    assert len(remove_reaction_calls) == 0, "remove_reaction should not be called"

@pytest.mark.asyncio
async def test_process_incoming_notification_data_no_genai_output(im_default_behavior_plugin, global_manager):
    # Setup
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        event_label="message",
        channel_id="C123",
        thread_id=None,
        response_id=None,
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123",
        is_mention=True,
        text="hello",
        origin_plugin_name="origin_plugin_name"
    )

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.genai_interactions_text_dispatcher = AsyncMock()
    im_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value=None)
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()

    # Add logging
    im_default_behavior_plugin.logger = MagicMock()

    # Execute
    await im_default_behavior_plugin.process_incoming_notification_data(event)

    # Print all logged messages
    print("\nLogged messages:")
    for call in im_default_behavior_plugin.logger.mock_calls:
        print(f"  {call}")

    # Print all method calls
    print("\nMethod calls:")
    for attr_name in dir(im_default_behavior_plugin):
        attr = getattr(im_default_behavior_plugin, attr_name)
        if isinstance(attr, AsyncMock):
            print(f"  {attr_name}:")
            for call in attr.mock_calls:
                print(f"    {call}")

    # Assert
    assert im_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request.called, \
        "genai_interactions_text_dispatcher.handle_request was not called"

    # Check that at least one reaction was added or removed
    assert (im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.called or
            im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.called), \
        "Neither add_reaction nor remove_reaction was called"

    # Check that no further processing occurred
    assert not im_default_behavior_plugin.global_manager.action_interactions_handler.handle_request.called, \
        "action_interactions_handler.handle_request was unexpectedly called"

@pytest.mark.asyncio
async def test_process_interaction_exception(im_default_behavior_plugin):
    event_data = {
        "text": "hello",
        "event_label": "message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "is_mention": True,
        "origin_plugin_name": "origin_plugin_name"
    }
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(side_effect=Exception("Test exception"))
    plugin_mock = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin = MagicMock(return_value=plugin_mock)

    with pytest.raises(Exception):
        await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    im_default_behavior_plugin.logger.error.assert_called()

@pytest.mark.asyncio
async def test_update_reaction(im_default_behavior_plugin):
    # Setup
    event = MagicMock()
    channel_id = "C123"
    timestamp = "1234567890.123456"
    remove_reaction = "old_reaction"
    add_reaction = "new_reaction"

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()

    # Execute
    await im_default_behavior_plugin.update_reaction(event, channel_id, timestamp, remove_reaction, add_reaction)

    # Assert
    im_default_behavior_plugin.user_interaction_dispatcher.remove_reaction.assert_called_once_with(
        event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=remove_reaction
    )
    im_default_behavior_plugin.user_interaction_dispatcher.add_reaction.assert_called_once_with(
        event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=add_reaction
    )
