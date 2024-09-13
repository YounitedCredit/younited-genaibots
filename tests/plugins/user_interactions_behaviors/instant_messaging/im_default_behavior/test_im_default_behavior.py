from unittest.mock import AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.user_interactions_behaviors.instant_messaging.im_default_behavior.im_default_behavior import (
    ImDefaultBehaviorPlugin,
    MessageType,
)


@pytest.fixture(scope="function", autouse=True)
def global_manager(mock_global_manager):
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.bot_config = MagicMock()
    mock_global_manager.bot_config.BREAK_KEYWORD = "break"
    mock_global_manager.bot_config.START_KEYWORD = "start"
    mock_global_manager.bot_config.REQUIRE_MENTION_NEW_MESSAGE = True
    yield mock_global_manager
    mock_global_manager.reset_mock()

@pytest.fixture(scope="function")
def im_default_behavior_plugin(global_manager):
    plugin = ImDefaultBehaviorPlugin(global_manager)
    plugin.initialize()
    yield plugin

@pytest.fixture(autouse=True)
def reset_mocks(im_default_behavior_plugin, global_manager):
    im_default_behavior_plugin.logger.reset_mock()
    global_manager.reset_mock()
    im_default_behavior_plugin.user_interaction_dispatcher.reset_mock()
    im_default_behavior_plugin.genai_interactions_text_dispatcher.reset_mock()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.reset_mock()
    yield

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
    global_manager.reset_mock()
    global_manager.user_interactions_dispatcher.reset_mock()
    global_manager.genai_interactions_text_dispatcher.reset_mock()
    global_manager.backend_internal_data_processing_dispatcher.reset_mock()
    global_manager.bot_config.reset_mock()
    im_default_behavior_plugin.logger.reset_mock()

    event_data = {
        "text": "hello",
        "event_label": "message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "thread_id": "thread_1",
        "response_id": "response_1",
        "user_name": "test_user",
        "user_email": "test_user@example.com",
        "user_id": "user_1",
        "is_mention": True,
        "origin": "origin_plugin"
    }
    event = IncomingNotificationDataBase.from_dict(event_data)

    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)

    plugin_mock = AsyncMock()
    plugin_mock.reactions = MagicMock(
        PROCESSING="processing",
        DONE="done",
        ACKNOWLEDGE="acknowledge",
        GENERATING="generating",
        WRITING="writing",
        ERROR="error",
        WAIT="wait"
    )
    plugin_mock.add_reaction = AsyncMock()
    plugin_mock.send_message = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin = MagicMock(return_value=plugin_mock)

    im_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value='{"text": "response"}')

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    plugin_mock.add_reaction.assert_awaited()
    plugin_mock.send_message.assert_awaited()
    plugin_mock.remove_reaction.assert_awaited()


@pytest.mark.asyncio
async def test_process_incoming_notification_data(im_default_behavior_plugin, global_manager):
    global_manager.reset_mock()
    global_manager.user_interactions_dispatcher.reset_mock()
    global_manager.genai_interactions_text_dispatcher.reset_mock()
    global_manager.backend_internal_data_processing_dispatcher.reset_mock()
    global_manager.bot_config.reset_mock()
    im_default_behavior_plugin.logger.reset_mock()

    event_data = {
        "text": "hello",
        "event_label": "message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "thread_id": "thread_1",
        "response_id": "response_1",
        "user_name": "test_user",
        "user_email": "test_user@example.com",
        "user_id": "user_1",
        "is_mention": True,
        "origin": "origin_plugin"
    }
    event = IncomingNotificationDataBase.from_dict(event_data)

    im_default_behavior_plugin.logger = MagicMock()

    plugin_mock = AsyncMock()
    plugin_mock.reactions = MagicMock(
        PROCESSING="processing",
        DONE="done",
        ACKNOWLEDGE="acknowledge",
        GENERATING="generating",
        WRITING="writing",
        ERROR="error",
        WAIT="wait"
    )
    plugin_mock.remove_reaction = AsyncMock()
    plugin_mock.add_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock

    im_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value='{"text": "response"}')

    im_default_behavior_plugin.reaction_done = "done"
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_writing = "writing"
    im_default_behavior_plugin.reaction_error = "error"

    await im_default_behavior_plugin.process_incoming_notification_data(event)
    plugin_mock.add_reaction.assert_awaited()
    plugin_mock.remove_reaction.assert_awaited()


@pytest.mark.asyncio
async def test_begin_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    plugin_mock = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    plugin_mock.add_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.reaction_writing = "writing"
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)

    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_writing)
    plugin_mock.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_generating)

@pytest.mark.asyncio
async def test_end_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    plugin_mock = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)

    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_generating)

@pytest.mark.asyncio
async def test_begin_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    plugin_mock = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    plugin_mock.add_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)

    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_generating)
    plugin_mock.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_processing)

@pytest.mark.asyncio
async def test_end_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    plugin_mock = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)

    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_processing)

@pytest.mark.asyncio
async def test_mark_error(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    plugin_mock = AsyncMock()
    plugin_mock.remove_reaction = AsyncMock()
    plugin_mock.add_reaction = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_error = "error"

    await im_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)

    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_generating)
    plugin_mock.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_error)

@pytest.mark.asyncio
async def test_process_interaction_none_event(im_default_behavior_plugin):
    await im_default_behavior_plugin.process_interaction(None)
    im_default_behavior_plugin.logger.debug.assert_called_with("No event")

@pytest.mark.asyncio
async def test_process_interaction_thread_break_keyword(im_default_behavior_plugin, global_manager):
    event_data = {
        "text": global_manager.bot_config.BREAK_KEYWORD,
        "event_label": "thread_message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "thread_id": "thread_1",
        "is_mention": True,
        "origin": "origin_plugin"
    }
    event = IncomingNotificationDataBase.from_dict(event_data)
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=event)
    plugin_mock = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin = MagicMock(return_value=plugin_mock)

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    plugin_mock.send_message.assert_awaited()
    global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

@pytest.mark.asyncio
async def test_process_interaction_break_keyword(im_default_behavior_plugin, global_manager):
    event_data = {
        "text": global_manager.bot_config.BREAK_KEYWORD,
        "event_label": "thread_message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "thread_id": "thread_1",
        "is_mention": True,
        "origin": "origin_plugin"
    }

    im_default_behavior_plugin.user_interaction_dispatcher = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(return_value=IncomingNotificationDataBase.from_dict(event_data))
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin = MagicMock()

    plugin_mock = AsyncMock()
    plugin_mock.reactions = MagicMock(
        PROCESSING="processing",
        DONE="done",
        ACKNOWLEDGE="acknowledge",
        GENERATING="generating",
        WRITING="writing",
        ERROR="error",
        WAIT="wait"
    )
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin.return_value = plugin_mock

    im_default_behavior_plugin.backend_internal_data_processing_dispatcher = AsyncMock()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    plugin_mock.send_message.assert_awaited()
    im_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_awaited()

@pytest.mark.asyncio
async def test_begin_end_genai_completion(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.instantmessaging_plugin = AsyncMock()
    im_default_behavior_plugin.reaction_writing = "writing"
    im_default_behavior_plugin.reaction_generating = "generating"

    await im_default_behavior_plugin.begin_genai_completion(event, event.channel_id, event.timestamp)
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="writing")
    im_default_behavior_plugin.instantmessaging_plugin.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating")

    await im_default_behavior_plugin.end_genai_completion(event, event.channel_id, event.timestamp)
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating")

@pytest.mark.asyncio
async def test_begin_end_long_action(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.instantmessaging_plugin = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_processing = "processing"

    await im_default_behavior_plugin.begin_long_action(event, event.channel_id, event.timestamp)
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating")
    im_default_behavior_plugin.instantmessaging_plugin.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing")

    await im_default_behavior_plugin.end_long_action(event, event.channel_id, event.timestamp)
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="processing")

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

    im_default_behavior_plugin.instantmessaging_plugin = AsyncMock()
    im_default_behavior_plugin.reaction_generating = "generating"
    im_default_behavior_plugin.reaction_error = "error"

    await im_default_behavior_plugin.mark_error(event, event.channel_id, event.timestamp)
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="generating")
    im_default_behavior_plugin.instantmessaging_plugin.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="error")

@pytest.mark.asyncio
async def test_update_reaction(im_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"

    im_default_behavior_plugin.instantmessaging_plugin = AsyncMock()

    await im_default_behavior_plugin.update_reaction(event, event.channel_id, event.timestamp, remove_reaction="old_reaction", add_reaction="new_reaction")
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="old_reaction")
    im_default_behavior_plugin.instantmessaging_plugin.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="new_reaction")

    # Test without adding a new reaction
    await im_default_behavior_plugin.update_reaction(event, event.channel_id, event.timestamp, remove_reaction="old_reaction")
    im_default_behavior_plugin.instantmessaging_plugin.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name="old_reaction")
    assert im_default_behavior_plugin.instantmessaging_plugin.add_reaction.call_count == 1  # Should not have been called again

@pytest.mark.asyncio
async def test_process_interaction_start_keyword(im_default_behavior_plugin, global_manager, monkeypatch):
    monkeypatch.setattr(global_manager.bot_config, 'START_KEYWORD', "start")
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="2023-01-01 12:00:00",
        event_label="thread_message",
        channel_id="C123",
        thread_id="thread_1",
        response_id="response_1",
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=True,
        text="start",
        origin="test_origin"
    )
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'request_to_notification_data', AsyncMock(return_value=event_data))
    plugin_mock = AsyncMock()
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'get_plugin', MagicMock(return_value=plugin_mock))

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    plugin_mock.send_message.assert_awaited()

@pytest.mark.asyncio
async def test_process_interaction_thread_message_no_mention(im_default_behavior_plugin, global_manager, monkeypatch):
    monkeypatch.setattr(global_manager.bot_config, 'REQUIRE_MENTION_THREAD_MESSAGE', True)
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="2023-01-01 12:00:00",
        event_label="thread_message",
        channel_id="C123",
        thread_id="thread_1",
        response_id="response_1",
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=False,
        text="Hello",
        origin="test_origin"
    )
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'request_to_notification_data', AsyncMock(return_value=event_data))
    plugin_mock = AsyncMock()
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'get_plugin', MagicMock(return_value=plugin_mock))

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    plugin_mock.send_message.assert_not_awaited()

@pytest.mark.asyncio
async def test_process_interaction_new_message_no_mention(im_default_behavior_plugin, global_manager, monkeypatch):
    monkeypatch.setattr(global_manager.bot_config, 'REQUIRE_MENTION_NEW_MESSAGE', True)
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="2023-01-01 12:00:00",
        event_label="message",
        channel_id="C123",
        thread_id=None,
        response_id=None,
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=False,
        text="Hello",
        origin="test_origin"
    )
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'request_to_notification_data', AsyncMock(return_value=event_data))
    plugin_mock = AsyncMock()
    monkeypatch.setattr(im_default_behavior_plugin.user_interaction_dispatcher, 'get_plugin', MagicMock(return_value=plugin_mock))

    await im_default_behavior_plugin.process_interaction(event_data.to_dict(), event_origin="test_origin")

    # Vérifications précédentes...

    # Examinons la structure des appels de méthode
    print("Nombre d'appels de méthode:", len(plugin_mock.method_calls))
    for i, call in enumerate(plugin_mock.method_calls):
        print(f"Appel {i}:")
        print("  Nom de la méthode:", call[0])
        print("  Arguments:", call[1])
        print("  Kwargs:", call[2])
        print()

    # Vérifications des appels spécifiques
    add_reaction_calls = [call for call in plugin_mock.method_calls if call[0] == 'add_reaction']
    send_message_calls = [call for call in plugin_mock.method_calls if call[0] == 'send_message']
    remove_reaction_calls = [call for call in plugin_mock.method_calls if call[0] == 'remove_reaction']

    assert len(add_reaction_calls) == 1, "add_reaction devrait être appelé une fois"
    assert len(send_message_calls) == 1, "send_message devrait être appelé une fois"
    assert len(remove_reaction_calls) == 1, "remove_reaction devrait être appelé une fois"

    # Vérifiez les arguments des appels
    add_reaction_args = add_reaction_calls[0][2]  # Utilisation des kwargs
    assert add_reaction_args['event'] == event_data
    assert add_reaction_args['channel_id'] == 'C123'
    assert add_reaction_args['timestamp'] == '1234567890.123456'
    assert 'reaction_name' in add_reaction_args

    send_message_args = send_message_calls[0][2]  # Utilisation des kwargs
    assert send_message_args['event'] == event_data
    assert send_message_args['message'] == ''
    assert send_message_args['message_type'] == MessageType.TEXT
    assert send_message_args['is_internal'] == True
    assert send_message_args['show_ref'] == True

    remove_reaction_args = remove_reaction_calls[0][2]  # Utilisation des kwargs
    assert remove_reaction_args['event'] == event_data
    assert remove_reaction_args['channel_id'] == 'C123'
    assert remove_reaction_args['timestamp'] == '1234567890.123456'
    assert 'reaction_name' in remove_reaction_args

@pytest.mark.asyncio
async def test_process_incoming_notification_data_no_genai_output(im_default_behavior_plugin, global_manager, monkeypatch):
    event_data = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="2023-01-01 12:00:00",
        event_label="message",
        channel_id="C123",
        thread_id=None,
        response_id=None,
        user_name="test_user",
        user_email="test@example.com",
        user_id="U123",
        is_mention=True,
        text="hello",
        origin="test_origin"
    )

    # Mock the instantmessaging_plugin
    plugin_mock = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock

    # Mock the genai_interactions_text_dispatcher
    monkeypatch.setattr(im_default_behavior_plugin.genai_interactions_text_dispatcher, 'handle_request', AsyncMock(return_value=None))

    # Mock the global_manager.bot_config
    monkeypatch.setattr(global_manager.bot_config, 'ACKNOWLEDGE_NONPROCESSED_MESSAGE', True)

    # Set up the reaction attributes
    im_default_behavior_plugin.reaction_done = "done_reaction"
    im_default_behavior_plugin.reaction_generating = "generating_reaction"
    im_default_behavior_plugin.reaction_writing = "writing_reaction"
    im_default_behavior_plugin.reaction_acknowledge = "acknowledge_reaction"

    await im_default_behavior_plugin.process_incoming_notification_data(event_data)

    # Verify the expected behavior
    plugin_mock.remove_reaction.assert_any_call(event=event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp, reaction_name=im_default_behavior_plugin.reaction_done)
    plugin_mock.remove_reaction.assert_any_call(event=event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp, reaction_name=im_default_behavior_plugin.reaction_generating)
    plugin_mock.remove_reaction.assert_any_call(event=event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp, reaction_name=im_default_behavior_plugin.reaction_writing)
    plugin_mock.remove_reaction.assert_any_call(event=event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp, reaction_name=im_default_behavior_plugin.reaction_acknowledge)

    im_default_behavior_plugin.logger.info.assert_called_with("GenAI output is None, not processing the message.")
    plugin_mock.add_reaction.assert_called_with(channel_id=event_data.channel_id, timestamp=event_data.timestamp, reaction_name=im_default_behavior_plugin.reaction_done)

    # Verify that no other interactions occurred
    assert not plugin_mock.send_message.called

@pytest.mark.asyncio
async def test_process_incoming_notification_data_exception(im_default_behavior_plugin):
    event_data = {
        "text": "hello",
        "event_label": "message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "is_mention": True,
        "origin": "origin_plugin"
    }
    event = IncomingNotificationDataBase.from_dict(event_data)

    plugin_mock = AsyncMock()
    im_default_behavior_plugin.instantmessaging_plugin = plugin_mock
    im_default_behavior_plugin.genai_interactions_text_dispatcher.handle_request = AsyncMock(side_effect=Exception("Test exception"))

    await im_default_behavior_plugin.process_incoming_notification_data(event)

    im_default_behavior_plugin.logger.error.assert_called()
    plugin_mock.remove_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_done)
    plugin_mock.add_reaction.assert_awaited_with(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=im_default_behavior_plugin.reaction_error)

@pytest.mark.asyncio
async def test_process_interaction_exception(im_default_behavior_plugin):
    event_data = {
        "text": "hello",
        "event_label": "message",
        "channel_id": "C123",
        "timestamp": "1234567890.123456",
        "is_mention": True,
        "origin": "origin_plugin"
    }
    im_default_behavior_plugin.user_interaction_dispatcher.request_to_notification_data = AsyncMock(side_effect=Exception("Test exception"))
    plugin_mock = AsyncMock()
    im_default_behavior_plugin.user_interaction_dispatcher.get_plugin = MagicMock(return_value=plugin_mock)

    with pytest.raises(Exception):
        await im_default_behavior_plugin.process_interaction(event_data, event_origin="test_origin")

    im_default_behavior_plugin.logger.error.assert_called()
