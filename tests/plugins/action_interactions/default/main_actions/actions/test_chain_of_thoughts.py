from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.chain_of_thoughts import (
    ChainOfThoughts,
)


@pytest.fixture
def chain_of_thoughts(mock_global_manager):
    return ChainOfThoughts(global_manager=mock_global_manager)

@pytest.fixture
def sample_event():
    return IncomingNotificationDataBase(
        timestamp="123456",
        event_label="test_event",
        channel_id="channel_1",
        thread_id="thread_123",
        response_id="response_123",
        user_name="test_user",
        user_email="test@example.com",
        user_id="user_123",
        is_mention=True,
        text="test text",
        origin_plugin_name="test_plugin"
    )

@pytest.mark.asyncio
async def test_execute_success(chain_of_thoughts, sample_event):
    action_input = ActionInput(
        action_name="test_action",
        parameters={
            'task': 'Test Task',
            'plan': ['Step 1', 'Step 2']
        }
    )

    chain_of_thoughts.user_interactions_dispatcher.send_message = AsyncMock()
    chain_of_thoughts.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    await chain_of_thoughts.execute(action_input, sample_event)

    chain_of_thoughts.user_interactions_dispatcher.send_message.assert_called_once_with(
        event=sample_event,
        message="Executing the task: Test Task",
        message_type=MessageType.TEXT,
        title="Task Execution",
        is_internal=False
    )
    assert chain_of_thoughts.genai_interactions_text_dispatcher.trigger_genai.call_count == 2

@pytest.mark.asyncio
async def test_execute_missing_parameters(chain_of_thoughts, sample_event):
    action_input = ActionInput(
        action_name="test_action",
        parameters={
            'task': 'Test Task'
        }
    )

    chain_of_thoughts.user_interactions_dispatcher.send_message = AsyncMock()

    await chain_of_thoughts.execute(action_input, sample_event)

    chain_of_thoughts.user_interactions_dispatcher.send_message.assert_called_once_with(
        event=sample_event,
        message="Error executing ChainOfThoughts: Missing 'task' or 'plan' in parameters",
        message_type=MessageType.TEXT,
        title="Error",
        is_internal=True
    )

@pytest.mark.asyncio
async def test_event_copy_integrity(chain_of_thoughts, sample_event):
    action_input = ActionInput(
        action_name="test_action",
        parameters={
            'task': 'Test Task',
            'plan': ['Step 1']
        }
    )

    original_event_dict = sample_event.to_dict()

    chain_of_thoughts.user_interactions_dispatcher.send_message = AsyncMock()
    chain_of_thoughts.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    await chain_of_thoughts.execute(action_input, sample_event)

    assert sample_event.to_dict() == original_event_dict

    modified_event = chain_of_thoughts.event
    assert modified_event.text == 'Step 1'
    assert modified_event.files_content == []
    assert modified_event.images == []
