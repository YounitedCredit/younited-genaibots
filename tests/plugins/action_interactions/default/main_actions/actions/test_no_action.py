# tests/plugins/action_interactions/default/main_actions/actions/test_no_action.py


import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.action_interactions.default.main_actions.actions.no_action import NoAction


@pytest.mark.asyncio
async def test_no_action_initialization(mock_global_manager):
    # Setup
    no_action = NoAction(global_manager=mock_global_manager)

    # Assert that the object is initialized correctly
    assert no_action.global_manager == mock_global_manager

@pytest.mark.asyncio
async def test_no_action_execute(mock_global_manager):
    # Setup
    no_action = NoAction(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='no_action', parameters={})
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

    # Mock methods if any (no methods to mock in this case)

    # Execute the action
    result = await no_action.execute(action_input, event)

    # Assert that the execute method completes without error
    assert result is None  # As the method does not return anything

# Add more test cases if additional functionality is added in the future
