# tests/plugins/action_interactions/default/main_actions/actions/test_long_text.py

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.action_interactions.default.main_actions.actions.long_text import LongText


@pytest.mark.asyncio
async def test_long_text_execution(mock_global_manager):
    # Setup
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': 'Test content', 'is_finished': False})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods
    mock_global_manager.backend_internal_data_processing_dispatcher.concatenate = "mock_concatenate_folder"
    mock_global_manager.backend_internal_data_processing_dispatcher.sessions = "mock_sessions_folder"
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    # Execute the action
    with patch.object(long_text_action, '_process_continuation', return_value=True) as mock_process_continuation:
        result = await long_text_action.execute(action_input, event)

    # Assert the correct behavior for non-finished text
    assert result is True
    mock_process_continuation.assert_called_once()

    # Modify the action input to simulate a finished text
    action_input.parameters['is_finished'] = True
    with patch.object(long_text_action, '_process_end_of_conversation', return_value=True) as mock_process_end:
        result = await long_text_action.execute(action_input, event)

    # Assert the correct behavior for finished text
    assert result is True
    mock_process_end.assert_called_once()

@pytest.mark.asyncio
async def test_process_continuation(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    # Initialiser l'attribut concatenate_folder
    long_text_action.concatenate_folder = "mock_concatenate_folder"

    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Existing content")
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )
    result = await long_text_action._process_continuation("New content", "channel_1-thread_123.txt", event)

    assert result is True
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        "mock_concatenate_folder", "channel_1-thread_123.txt", "Existing content \n\nNew content"
    )
    mock_global_manager.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@pytest.mark.asyncio
async def test_process_end_of_conversation(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    long_text_action.concatenate_folder = "mock_concatenate_folder"
    long_text_action.sessions_folder = "mock_sessions_folder"

    fake_session = MagicMock()
    fake_session.messages = []
    fake_session.session_id = "test_session_id"

    mock_global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(return_value=fake_session)
    mock_global_manager.session_manager_dispatcher.save_session = AsyncMock()
    mock_global_manager.session_manager_dispatcher.append_messages = MagicMock()
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Existing content")
    mock_global_manager.backend_internal_data_processing_dispatcher.remove_data_content = AsyncMock()
    mock_global_manager.user_interactions_dispatcher.upload_file = AsyncMock()

    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    result = await long_text_action._process_end_of_conversation("Final content", "channel_1-thread_123.txt", event)

    assert result is True
    mock_global_manager.session_manager_dispatcher.get_or_create_session.assert_called_once()
    mock_global_manager.session_manager_dispatcher.append_messages.assert_called_once()
    mock_global_manager.session_manager_dispatcher.save_session.assert_called_once_with(fake_session)
    mock_global_manager.backend_internal_data_processing_dispatcher.remove_data_content.assert_called_once()
    assert mock_global_manager.user_interactions_dispatcher.upload_file.call_count == 2

@pytest.mark.asyncio
async def test_long_text_execution_error_handling(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': 'Test content', 'is_finished': False})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin_plugin_name='test_plugin'
    )

    # Simulate an exception in _process_continuation
    with patch.object(long_text_action, '_process_continuation', side_effect=Exception("Test error")):
        result = await long_text_action.execute(action_input, event)
    assert result is False

@pytest.mark.asyncio
async def test_long_text_execution_empty_value(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': '', 'is_finished': False})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin_plugin_name='test_plugin'
    )

    with patch.object(long_text_action, '_process_continuation', return_value=True) as mock_process_continuation:
        result = await long_text_action.execute(action_input, event)

    assert result is True
    mock_process_continuation.assert_called_once_with('', 'channel_1-thread_1.txt', event)

@pytest.mark.asyncio
async def test_process_continuation_error(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    long_text_action.concatenate_folder = "mock_concatenate_folder"

    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=Exception("Read error"))

    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin_plugin_name='test_plugin'
    )
    result = await long_text_action._process_continuation("New content", "channel_1-123456.txt", event)

    assert result is False

@pytest.mark.asyncio
async def test_process_end_of_conversation_error(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    long_text_action.concatenate_folder = "mock_concatenate_folder"
    long_text_action.sessions_folder = "mock_sessions_folder"

    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=Exception("Read error"))

    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin_plugin_name='test_plugin'
    )
    result = await long_text_action._process_end_of_conversation("Final content", "channel_1-123456.txt", event)

    assert result is False
