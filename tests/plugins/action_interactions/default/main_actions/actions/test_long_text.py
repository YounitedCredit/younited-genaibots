# tests/plugins/action_interactions/default/main_actions/actions/test_long_text.py

from unittest.mock import AsyncMock, patch
import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import IncomingNotificationDataBase
from plugins.action_interactions.default.main_actions.actions.long_text import LongText

@pytest.mark.asyncio
async def test_long_text_execution(mock_global_manager):
    # Setup
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': 'Test content', 'is_finished': False})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        converted_timestamp='2024-07-03T12:34:56Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[]
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
        converted_timestamp='2024-07-03T12:34:56Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[]
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
    # Initialiser les attributs nécessaires
    long_text_action.concatenate_folder = "mock_concatenate_folder"
    long_text_action.sessions_folder = "mock_sessions_folder"
    
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Existing content")
    mock_global_manager.backend_internal_data_processing_dispatcher.update_session = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher.remove_data_content = AsyncMock()
    mock_global_manager.user_interactions_dispatcher.upload_file = AsyncMock()

    event = IncomingNotificationDataBase(
        timestamp='123456',
        converted_timestamp='2024-07-03T12:34:56Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[]
    )
    result = await long_text_action._process_end_of_conversation("Final content", "channel_1-thread_123.txt", event)

    assert result is True
    mock_global_manager.backend_internal_data_processing_dispatcher.update_session.assert_called_once_with(
        "mock_sessions_folder", "channel_1-thread_123.txt", "assistant", "Existing content \n\nFinal content"
    )
    mock_global_manager.backend_internal_data_processing_dispatcher.remove_data_content.assert_called_once()
    assert mock_global_manager.user_interactions_dispatcher.upload_file.call_count == 2

@pytest.mark.asyncio
async def test_long_text_execution_error_handling(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': 'Test content', 'is_finished': False})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        converted_timestamp='2023-01-01T12:00:00Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin='test_origin'
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
        converted_timestamp='2023-01-01T12:00:00Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin='test_origin'
    )

    with patch.object(long_text_action, '_process_continuation', return_value=True) as mock_process_continuation:
        result = await long_text_action.execute(action_input, event)
    
    assert result is True
    mock_process_continuation.assert_called_once_with('', 'channel_1-thread_1.txt', event)

@pytest.mark.asyncio
async def test_long_text_execution_no_thread_id(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='long_text', parameters={'value': 'Test', 'is_finished': True})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        converted_timestamp='2023-01-01T12:00:00Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id=None,
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin='test_origin'
    )

    with patch.object(long_text_action, '_process_end_of_conversation', return_value=True) as mock_process_end:
        result = await long_text_action.execute(action_input, event)
    
    assert result is True
    # Vérifier que _process_end_of_conversation a été appelé avec le bon nom de fichier
    mock_process_end.assert_called_once_with('Test', 'channel_1-123456.txt', event)
    # Vérifier que thread_id est toujours None (car il n'est pas modifié dans execute)
    assert event.thread_id is None

@pytest.mark.asyncio
async def test_process_continuation_error(mock_global_manager):
    long_text_action = LongText(global_manager=mock_global_manager)
    long_text_action.concatenate_folder = "mock_concatenate_folder"
    
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=Exception("Read error"))

    event = IncomingNotificationDataBase(
        timestamp='123456',
        converted_timestamp='2023-01-01T12:00:00Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin='test_origin'
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
        converted_timestamp='2023-01-01T12:00:00Z',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_1',
        response_id='response_1',
        user_name='test_user',
        user_email='test@example.com',
        user_id='user_1',
        is_mention=False,
        text='Test text',
        origin='test_origin'
    )
    result = await long_text_action._process_end_of_conversation("Final content", "channel_1-123456.txt", event)

    assert result is False