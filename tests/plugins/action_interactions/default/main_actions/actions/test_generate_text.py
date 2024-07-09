import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.generate_text import (
    GenerateText,  # Remplacez `mymodule` par le chemin correct de votre module
)


@pytest.mark.asyncio
async def test_generate_text_execute(mock_global_manager):
    # Initialize the action with the mocked global manager
    action = GenerateText(mock_global_manager)

    # Create mock objects for ActionInput and IncomingNotificationDataBase
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'text': 'Test text',
            'model_name': 'TestModel',
            'context': 'Test context',
            'conversation': True
        }
    )

    event = IncomingNotificationDataBase(
        timestamp="2023-07-03T12:34:56Z",
        converted_timestamp="2023-07-03T12:34:56Z",
        event_label="test_event",
        channel_id='channel_123',
        thread_id='thread_456',
        response_id='response_789',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='test text',
        origin='test_origin'
    )

    # Mock necessary methods and attributes
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value='[{"role": "user", "content": "Hello"}]')
    mock_global_manager.genai_interactions_text_dispatcher.plugins = [MagicMock(plugin_name='TestModel')]
    mock_global_manager.genai_interactions_text_dispatcher.handle_action = AsyncMock(return_value='Generated response')
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    # Execute the action
    await action.execute(action_input, event)

    # Assert the interactions
    mock_global_manager.user_interactions_dispatcher.send_message.assert_any_call(
        "Invoking model TestModel...", event, message_type=MessageType.COMMENT)
    mock_global_manager.genai_interactions_text_dispatcher.handle_action.assert_awaited_once()
    mock_global_manager.user_interactions_dispatcher.send_message.assert_any_call('Generated response', event)

    # Additional assertions for conversation processing
    assert json.loads(action_input.parameters['conversation_data']) == [{"role": "user", "content": "Hello"}]

@pytest.mark.asyncio
async def test_generate_text_execute_model_not_exists(mock_global_manager):
    # Initialize the action with the mocked global manager
    action = GenerateText(mock_global_manager)

    # Create mock objects for ActionInput and IncomingNotificationDataBase
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'text': 'Test text',
            'model_name': 'NonExistentModel',
            'context': 'Test context'
        }
    )

    event = IncomingNotificationDataBase(
        timestamp="2023-07-03T12:34:56Z",
        converted_timestamp="2023-07-03T12:34:56Z",
        event_label="test_event",
        channel_id='channel_123',
        thread_id='thread_456',
        response_id='response_789',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='test text',
        origin='test_origin'
    )

    # Mock necessary methods and attributes
    mock_global_manager.genai_interactions_text_dispatcher.plugins = []
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    # Execute the action
    await action.execute(action_input, event)

    # Assert the interactions
    mock_global_manager.logger.error.assert_called_once_with("The model NonExistentModel does not exist.")
    mock_global_manager.user_interactions_dispatcher.send_message.assert_any_call(
        "Invalid GenAI model called [NonExistentModel] contact the bot owner if the problem persists.]", event, "comment")

@pytest.mark.asyncio
async def test_generate_text_execute_exception_handling(mock_global_manager):
    # Initialize the action with the mocked global manager
    action = GenerateText(mock_global_manager)

    # Create mock objects for ActionInput and IncomingNotificationDataBase
    action_input = ActionInput(
        action_name='GenerateText',
        parameters={
            'text': 'Test text',
            'model_name': 'TestModel',
            'context': 'Test context'
        }
    )

    event = IncomingNotificationDataBase(
        timestamp="2023-07-03T12:34:56Z",
        converted_timestamp="2023-07-03T12:34:56Z",
        event_label="test_event",
        channel_id='channel_123',
        thread_id='thread_456',
        response_id='response_789',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='test text',
        origin='test_origin'
    )

    # Mock necessary methods and attributes to raise an exception
    mock_global_manager.genai_interactions_text_dispatcher.plugins = [MagicMock(plugin_name='TestModel')]
    mock_global_manager.genai_interactions_text_dispatcher.handle_action = AsyncMock(side_effect=Exception("Test exception"))
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()
    mock_global_manager.logger.error = MagicMock()

    # Execute the action
    await action.execute(action_input, event)

    # Assert the interactions
    mock_global_manager.logger.error.assert_called_once()
    assert "An error occurred: Test exception" in mock_global_manager.logger.error.call_args[0][0]


