# tests/plugins/action_interactions/default/main_actions/actions/test_user_interaction.py

from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.user_interaction import (
    UserInteraction,
)


@pytest.mark.asyncio
async def test_user_interaction_initialization(mock_global_manager):
    # Setup
    user_interaction_action = UserInteraction(global_manager=mock_global_manager)

    # Assert that the object is initialized correctly
    assert user_interaction_action.global_manager == mock_global_manager

@pytest.mark.asyncio
async def test_user_interaction_execute(mock_global_manager):
    # Setup
    user_interaction_action = UserInteraction(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='user_interaction', parameters={'value': 'Test message'})
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
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name="origin_plugin_name"
    )

    # Mock methods
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    # Execute the action
    await user_interaction_action.execute(action_input, event)

    # Assert that send_message was called correctly
    mock_global_manager.user_interactions_dispatcher.send_message.assert_any_call(
        event=event,
        message='Test message',
        message_type=MessageType.TEXT
    )
    mock_global_manager.user_interactions_dispatcher.send_message.assert_any_call(
        event=event,
        message=':speaking_head_in_silhouette: *UserInteraction:* Test message',
        message_type=MessageType.TEXT,
        is_internal=True
    )

@pytest.mark.asyncio
async def test_user_interaction_execute_empty_message(mock_global_manager):
    # Setup
    user_interaction_action = UserInteraction(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='user_interaction', parameters={'value': ''})
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
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Assert that ValueError is raised
    with pytest.raises(ValueError, match="Empty message"):
        await user_interaction_action.execute(action_input, event)

# Add more test cases to cover different scenarios and edge cases
