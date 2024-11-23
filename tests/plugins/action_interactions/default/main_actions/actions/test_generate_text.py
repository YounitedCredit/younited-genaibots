from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.generate_text import (
    GenerateText,
)

@pytest.mark.asyncio
async def test_generate_text_execute(mock_global_manager):
    action = GenerateText(mock_global_manager)
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'model_name': 'TestModel',
            'input': 'Test input',
            'main_prompt': 'Test prompt',
            'conversation': True,
            'context': 'Test context'
        }
    )

    event = IncomingNotificationDataBase(
        timestamp="2023-07-03T12:34:56Z",
        event_label="test_event",
        channel_id='channel_123',
        thread_id='thread_456',
        response_id='response_789',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='test text',
        origin_plugin_name='test_plugin'
    )

    # Configuration correcte des mocks
    mock_session = MagicMock()
    mock_session.messages = [{"role": "user", "content": "Hello"}]
    
    mock_global_manager.prompt_manager.get_main_prompt = AsyncMock(return_value="Test main prompt")
    mock_global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(return_value=mock_session)
    mock_global_manager.genai_interactions_text_dispatcher.plugins = [MagicMock(plugin_name='TestModel')]
    mock_global_manager.genai_interactions_text_dispatcher.handle_action = AsyncMock(return_value='Generated response')
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    await action.execute(action_input, event)

    expected_messages = [
        {"role": "system", "content": "Test main prompt"},
        {"role": "user", "content": "user: Hello"},
        {"role": "user", "content": "with the following context: Test context\n\nhere's the user query: Test input"}
    ]
    actual_messages = mock_global_manager.genai_interactions_text_dispatcher.handle_action.call_args[0][0].parameters['messages']
    assert actual_messages == expected_messages

@pytest.mark.asyncio
async def test_generate_text_execute_no_main_prompt(mock_global_manager):
    action = GenerateText(mock_global_manager)
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'model_name': 'TestModel',
            'input': 'Test input',
            'conversation': False
        }
    )
    event = MagicMock()

    mock_global_manager.genai_interactions_text_dispatcher.plugins = [MagicMock(plugin_name='TestModel')]
    mock_global_manager.genai_interactions_text_dispatcher.handle_action = AsyncMock(return_value='Generated response')
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    await action.execute(action_input, event)

    expected_messages = [
        {"role": "system", "content": "No specific instruction provided."},
        {"role": "user", "content": "Test input"}
    ]
    actual_messages = mock_global_manager.genai_interactions_text_dispatcher.handle_action.call_args[0][0].parameters['messages']
    assert actual_messages == expected_messages

@pytest.mark.asyncio
async def test_generate_text_execute_model_not_exists(mock_global_manager):
    action = GenerateText(mock_global_manager)
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'model_name': 'NonExistentModel',
            'input': 'Test input'
        }
    )
    event = MagicMock()

    mock_global_manager.genai_interactions_text_dispatcher.plugins = []
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    await action.execute(action_input, event)

    mock_global_manager.logger.error.assert_called_once_with("The model NonExistentModel does not exist.")
    mock_global_manager.user_interactions_dispatcher.send_message.assert_called_with(
        message="Invalid GenAI model called [NonExistentModel]. Contact the bot owner if the problem persists.",
        event=event,
        message_type=MessageType.COMMENT,
        action_ref="generate_text"
    )

@pytest.mark.asyncio
async def test_generate_text_execute_exception_handling(mock_global_manager):
    action = GenerateText(mock_global_manager)
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'model_name': 'TestModel',
            'input': 'Test input'
        }
    )
    event = MagicMock()

    mock_global_manager.genai_interactions_text_dispatcher.plugins = [MagicMock(plugin_name='TestModel')]
    mock_global_manager.genai_interactions_text_dispatcher.handle_action = AsyncMock(side_effect=Exception("Test exception"))
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    await action.execute(action_input, event)

    mock_global_manager.logger.error.assert_called_once()
    assert "An error occurred: Test exception" in mock_global_manager.logger.error.call_args[0][0]
    mock_global_manager.user_interactions_dispatcher.send_message.assert_called_with(
        message="An error occurred while processing your request: Test exception",
        event=event,
        message_type=MessageType.COMMENT
    )

@pytest.mark.asyncio
async def test_generate_text_execute_missing_parameters(mock_global_manager):
    action = GenerateText(mock_global_manager)
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={}
    )
    event = MagicMock()

    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    await action.execute(action_input, event)

    mock_global_manager.user_interactions_dispatcher.send_message.assert_called_with(
        message="Error: Missing mandatory parameters 'model_name' or 'input'.",
        event=event,
        message_type=MessageType.COMMENT
    )
