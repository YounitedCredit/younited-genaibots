from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.observation_thought import (
    ObservationThought,
)


@pytest.mark.asyncio
async def test_observation_thought_execute(mock_global_manager):
    # Setup
    observation_thought_action = ObservationThought(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='observation_thought', parameters={
        'observation': 'Test Observation',
        'thought': 'Test Thought',
        'plan': 'Test Plan',
        'nextstep': 'Test Next Step',
        'autoeval': 'Test Autoeval',
        'autoevaljustification': 'Test Autoeval Justification',
        'usermood': 'Test User Mood'
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
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
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock(return_value=True)

    # Execute the action
    await observation_thought_action.execute(action_input, event)

    # Assert that send_message was called with the correct parameters
    expected_message = (
        ":mag: *Observation*: Test Observation \n\n "
        ":brain: *Thought*: Test Thought \n\n "
        ":clipboard: *Plan*: Test Plan \n\n "
        ":rocket: *Next Step*: Test Next Step \n\n "
        ":bar_chart: *Autoeval*: Test Autoeval \n\n "
        ":straight_ruler: *Autoeval Justification*: Test Autoeval Justification \n\n "
        ":smiley: *User Mood*: Test User Mood"
    )

    mock_global_manager.user_interactions_dispatcher.send_message.assert_called_once_with(
        event=event,
        message=expected_message,
        message_type=MessageType.TEXT,
        title=None,
        is_internal=True
    )


@pytest.mark.asyncio
async def test_observation_thought_execute_with_missing_parameters(mock_global_manager):
    # Setup
    observation_thought_action = ObservationThought(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='observation_thought', parameters={})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
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
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock(return_value=True)

    # Execute the action
    await observation_thought_action.execute(action_input, event)

    # Assert that send_message was called with the default parameters
    expected_message = (
        ":mag: *Observation*: No Observation \n\n "
        ":brain: *Thought*: No Thought \n\n "
        ":clipboard: *Plan*: No Plan \n\n "
        ":rocket: *Next Step*: No Next Step \n\n "
        ":bar_chart: *Autoeval*: No Autoeval \n\n "
        ":straight_ruler: *Autoeval Justification*: No Autoeval Justification \n\n "
        ":smiley: *User Mood*: No User Mood"
    )

    mock_global_manager.user_interactions_dispatcher.send_message.assert_called_once_with(
        event=event,
        message=expected_message,
        message_type=MessageType.TEXT,
        title=None,
        is_internal=True
    )


@pytest.mark.asyncio
async def test_observation_thought_execute_with_exception(mock_global_manager):
    # Setup
    observation_thought_action = ObservationThought(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='observation_thought', parameters={})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods to raise an exception
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock(side_effect=Exception("Test exception"))

    # Execute the action
    await observation_thought_action.execute(action_input, event)

    # Assert that the exception was handled and printed
    # Note: This test assumes that the print function is not mocked
    # You might want to use a mocked logger instead of print for better testing
    # assert mock_logger.error.called_once_with("An error occurred while sending the message: Test exception")
