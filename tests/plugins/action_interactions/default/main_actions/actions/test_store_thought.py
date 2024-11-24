from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.store_thought import (
    StoreThought,
)


@pytest.fixture
def store_thought(mock_global_manager):
    return StoreThought(global_manager=mock_global_manager)

@pytest.fixture
def sample_event():
    return IncomingNotificationDataBase(
        timestamp="123456",
        event_label="test_event",
        channel_id="channel_1",
        thread_id="thread_123",
        response_id="response_123",
        is_mention=True,
        text="test text",
        origin_plugin_name="test_plugin"
    )

@pytest.mark.asyncio
async def test_execute_last_step(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Final result',
            'step': '2',
            'laststep': True
        }
    )

    stored_files = ["channel_1-thread_123-123456-1", "channel_1-thread_123-123456-2"]

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=stored_files)
    store_thought.global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Step content")
    store_thought.global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    result = await store_thought.execute(action_input, sample_event)

    assert result is True
    assert store_thought.global_manager.user_interactions_dispatcher.send_message.call_count == 2

@pytest.mark.asyncio
async def test_execute_missing_result(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'step': '1'
        }
    )

    result = await store_thought.execute(action_input, sample_event)

    assert result is False
    store_thought.global_manager.logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_execute_missing_step(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result'
        }
    )

    result = await store_thought.execute(action_input, sample_event)

    assert result is False
    store_thought.global_manager.logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_execute_error_handling(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result',
            'step': '1'
        }
    )

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock(side_effect=Exception("Test error"))

    result = await store_thought.execute(action_input, sample_event)

    assert result is False
    store_thought.global_manager.logger.error.assert_called_once_with("Failed to store thought: Test error")

@pytest.mark.asyncio
async def test_execute_success(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result',
            'step': '1',
            'laststep': False
        }
    )

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts = "chainofthoughts"

    result = await store_thought.execute(action_input, sample_event)

    assert result is True
    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        data_container=store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts,
        data_file="channel_1-thread_123-123456-1.txt",
        data="Test result"
    )

@pytest.mark.asyncio
async def test_execute_last_step_multiple_files(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Final result',
            'step': '3',
            'laststep': True
        }
    )

    stored_files = [
        "channel_1-thread_123-123456-1",
        "channel_1-thread_123-123456-2",
        "channel_1-thread_123-123456-3"
    ]

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=stored_files)
    store_thought.global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts = "chainofthoughts"
    store_thought.global_manager.user_interactions_dispatcher.send_message = AsyncMock()

    step_contents = {
        "channel_1-thread_123-123456-1.txt": "Step 1 content",
        "channel_1-thread_123-123456-2.txt": "Step 2 content",
        "channel_1-thread_123-123456-3.txt": "Step 3 content"
    }

    async def mock_read_content(data_container, data_file):
        return step_contents[data_file]

    store_thought.global_manager.backend_internal_data_processing_dispatcher.read_data_content.side_effect = mock_read_content

    result = await store_thought.execute(action_input, sample_event)

    assert result is True
    assert store_thought.global_manager.user_interactions_dispatcher.send_message.call_count == 3

    for i, content in enumerate(["Step 1 content", "Step 2 content", "Step 3 content"], 1):
        store_thought.global_manager.user_interactions_dispatcher.send_message.assert_any_call(
            event=sample_event,
            message=f"Step {i}: {content}",
            message_type=MessageType.TEXT,
            title=f"Step {i} Result",
            is_internal=False
        )

@pytest.mark.asyncio
async def test_execute_error_during_file_listing(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result',
            'step': '1',
            'laststep': True
        }
    )

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(
        side_effect=Exception("File listing error")
    )
    store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts = "chainofthoughts"

    result = await store_thought.execute(action_input, sample_event)

    assert result is False
    store_thought.global_manager.logger.error.assert_called_once_with(
        "Failed to store thought: File listing error"
    )

@pytest.mark.asyncio
async def test_execute_error_during_read(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result',
            'step': '1',
            'laststep': True
        }
    )

    stored_files = ["channel_1-thread_123-123456-1"]

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=stored_files)
    store_thought.global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(
        side_effect=Exception("Read error")
    )
    store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts = "chainofthoughts"

    result = await store_thought.execute(action_input, sample_event)

    assert result is False
    store_thought.global_manager.logger.error.assert_called_once_with(
        "Failed to store thought: Read error"
    )

@pytest.mark.asyncio
async def test_execute_no_matching_files(store_thought, sample_event):
    action_input = ActionInput(
        action_name="store_thought",
        parameters={
            'result': 'Test result',
            'step': '1',
            'laststep': True
        }
    )

    stored_files = ["different-thread-id-123456-1"]

    store_thought.global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    store_thought.global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=stored_files)
    store_thought.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts = "chainofthoughts"

    result = await store_thought.execute(action_input, sample_event)

    assert result is True
    assert store_thought.global_manager.user_interactions_dispatcher.send_message.call_count == 0
