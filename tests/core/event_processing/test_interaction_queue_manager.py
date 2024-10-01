import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.event_processing.interaction_queue_manager import InteractionQueueManager


@pytest.fixture
def mock_global_manager(mock_config_manager, mock_plugins):
    mock_global_manager = MagicMock()
    mock_global_manager.logger = MagicMock()
    mock_global_manager.backend_internal_queue_processing_dispatcher = MagicMock()
    mock_global_manager.user_interactions_dispatcher = MagicMock()
    return mock_global_manager

@pytest.fixture
def interaction_queue_manager(mock_global_manager):
    return InteractionQueueManager(global_manager=mock_global_manager)

@pytest.mark.asyncio
async def test_save_event_to_backend(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    interaction_queue_manager.internal_event_container = MagicMock()

    event_data = {
        'full_message_id': 'channel1_thread1_123456789_event123',
        'method_params': {'is_internal': True}
    }

    await interaction_queue_manager.save_event_to_backend(event_data, channel_id='channel1', thread_id='thread1')

    # Ensure the async function was awaited correctly
    await asyncio.sleep(0.1)  # Add a short sleep to allow async task to process
    mock_backend_dispatcher.enqueue_message.assert_awaited_once()

# Test the initialization of the InteractionQueueManager
def test_interaction_queue_manager_initialization(interaction_queue_manager, mock_global_manager):
    interaction_queue_manager.initialize()
    
    # Assert that event containers are set correctly from the global manager's backend dispatcher
    assert interaction_queue_manager.internal_event_container == mock_global_manager.backend_internal_queue_processing_dispatcher.internal_events_queue
    assert interaction_queue_manager.external_event_container == mock_global_manager.backend_internal_queue_processing_dispatcher.external_events_queue

    # Check if the logger has been called to confirm initialization
    interaction_queue_manager.logger.info.assert_called_with("InteractionQueueManager initialized.")

# Test adding an event to the internal queue
@pytest.mark.asyncio
async def test_add_to_queue_internal(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    method_params = {
        'channel_id': 'channel1',
        'thread_id': 'thread1',
        'timestamp': '123456789',
        'is_internal': True
    }

    # Add an event to the internal queue
    await interaction_queue_manager.add_to_queue(event_type='send_message', method_params=method_params)

    # Assert that the event is added to the internal queue and that the processing task is started
    queue_key = ('channel1', 'thread1')
    assert not interaction_queue_manager.internal_queues[queue_key].empty()

    interaction_queue_manager.logger.debug.assert_any_call(
        "Added send_message to internal queue ('channel1', 'thread1') with params: {'channel_id': 'channel1', 'thread_id': 'thread1', 'timestamp': '123456789', 'is_internal': True}"
    )


# Test adding an event to the external queue
@pytest.mark.asyncio
async def test_add_to_queue_external(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    method_params = {
        'channel_id': 'channel2',
        'thread_id': 'thread2',
        'timestamp': '987654321',
        'is_internal': False
    }

    # Add an event to the external queue
    await interaction_queue_manager.add_to_queue(event_type='upload_file', method_params=method_params)

    # Assert that the event is added to the external queue and that the processing task is started
    queue_key = ('channel2', 'thread2')
    assert not interaction_queue_manager.external_queues[queue_key].empty()

    interaction_queue_manager.logger.debug.assert_any_call(
        "Added upload_file to external queue ('channel2', 'thread2') with params: {'channel_id': 'channel2', 'thread_id': 'thread2', 'timestamp': '987654321', 'is_internal': False}"
    )

@pytest.mark.asyncio
async def test_process_internal_queue(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.send_message = AsyncMock()

    queue_key = ('channel1', 'thread1')
    event_data = {
        'event_type': 'send_message',
        'method_params': {'channel_id': 'channel1', 'thread_id': 'thread1', 'is_internal': True}
    }

    await interaction_queue_manager.internal_queues[queue_key].put(event_data)

    task = asyncio.create_task(interaction_queue_manager.process_internal_queue(queue_key))

    # Increase the wait time to give enough time for the task to execute
    await asyncio.sleep(0.5)

    dispatcher.send_message.assert_awaited_once()

    # Clean up the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_process_external_queue(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.upload_file = AsyncMock()

    queue_key = ('channel2', 'thread2')
    event_data = {
        'event_type': 'upload_file',
        'method_params': {'channel_id': 'channel2', 'thread_id': 'thread2', 'is_internal': False}
    }

    await interaction_queue_manager.external_queues[queue_key].put(event_data)

    task = asyncio.create_task(interaction_queue_manager.process_external_queue(queue_key))

    # Increase the wait time to give enough time for the task to execute
    await asyncio.sleep(0.5)

    dispatcher.upload_file.assert_awaited_once()

    # Clean up the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
