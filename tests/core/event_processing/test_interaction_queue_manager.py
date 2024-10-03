import asyncio
from unittest.mock import AsyncMock, MagicMock
import json
import pytest

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
    # Mock the backend dispatcher
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    event_data = {
        'full_message_id': 'channel1_thread1_123456789_event123',
        'message_id': '123456789',
        'guid': 'event123',  # Add the guid key to match the function's expectation
        'method_params': {'is_internal': True}
    }

    interaction_queue_manager.internal_event_container = MagicMock()
    interaction_queue_manager.backend_dispatcher = mock_backend_dispatcher

    # Call the method under test
    await interaction_queue_manager.save_event_to_backend(event_data, channel_id='channel1', thread_id='thread1')

    # Check if enqueue_message was called with the correct arguments
    mock_backend_dispatcher.enqueue_message.assert_called_once_with(
        data_container=interaction_queue_manager.internal_event_container,
        channel_id='channel1',
        thread_id='thread1',
        message_id='123456789',
        message=json.dumps(event_data),
        guid='event123'
    )
    
# Test the initialization of the InteractionQueueManager
def test_interaction_queue_manager_initialization(interaction_queue_manager, mock_global_manager):
    interaction_queue_manager.initialize()

    # Assert that event containers are set correctly from the global manager's backend dispatcher
    assert interaction_queue_manager.internal_event_container == mock_global_manager.backend_internal_queue_processing_dispatcher.internal_events_queue
    assert interaction_queue_manager.external_event_container == mock_global_manager.backend_internal_queue_processing_dispatcher.external_events_queue

    # Check if the expected logs were called
    interaction_queue_manager.logger.info.assert_any_call("InteractionQueueManager initialized.")
    interaction_queue_manager.logger.info.assert_any_call("Running synchronous cleanup of expired messages.")

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

    # Add event to the internal queue
    await interaction_queue_manager.internal_queues[queue_key].put(event_data)

    # Run the internal queue processor
    await interaction_queue_manager.process_internal_queue(queue_key)

    # Assert send_message was awaited
    dispatcher.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_internal_queue(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.send_message = AsyncMock()

    queue_key = ('channel1', 'thread1')
    event_data = {
        'event_type': 'send_message',
        'method_params': {'channel_id': 'channel1', 'thread_id': 'thread1', 'is_internal': True}
    }

    # Initialize the internal_processing_tasks dictionary
    interaction_queue_manager.internal_processing_tasks = {queue_key: asyncio.create_task(asyncio.sleep(0))}

    # Add event to the internal queue
    await interaction_queue_manager.internal_queues[queue_key].put(event_data)

    # Set up the mock for user_interaction_dispatcher
    interaction_queue_manager.user_interaction_dispatcher = dispatcher

    # Run the internal queue processor
    await interaction_queue_manager.process_internal_queue(queue_key)

    # Assert send_message was called
    dispatcher.send_message.assert_called_once_with(
        channel_id='channel1', thread_id='thread1', is_internal=True, is_replayed=True
    )

@pytest.mark.asyncio
async def test_process_external_queue(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.upload_file = AsyncMock()

    queue_key = ('channel2', 'thread2')
    event_data = {
        'event_type': 'upload_file',
        'method_params': {'channel_id': 'channel2', 'thread_id': 'thread2', 'is_internal': False}
    }

    # Initialize the external_processing_tasks dictionary
    interaction_queue_manager.external_processing_tasks = {queue_key: asyncio.create_task(asyncio.sleep(0))}

    # Add event to the external queue
    await interaction_queue_manager.external_queues[queue_key].put(event_data)

    # Set up the mock for user_interaction_dispatcher
    interaction_queue_manager.user_interaction_dispatcher = dispatcher

    # Run the external queue processor
    await interaction_queue_manager.process_external_queue(queue_key)

    # Assert upload_file was called
    dispatcher.upload_file.assert_called_once_with(
        channel_id='channel2', thread_id='thread2', is_internal=False, is_replayed=True
    )