import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.event_processing.interaction_queue_manager import (
    InteractionQueueManager,
    make_serializable,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


@pytest.fixture
def mock_global_manager(mock_config_manager, mock_plugins):
    mock_global_manager = MagicMock()
    mock_global_manager.logger = MagicMock()
    mock_global_manager.backend_internal_queue_processing_dispatcher = MagicMock()
    mock_global_manager.user_interactions_dispatcher = MagicMock()
    return mock_global_manager

@pytest.fixture(autouse=True)
async def cleanup_pending_tasks():
    yield
    # Clean up any pending tasks after each test
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

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
    # Setup du dispatcher
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.send_message = AsyncMock()
    interaction_queue_manager.user_interaction_dispatcher = dispatcher
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()

    queue_key = ('channel1', 'thread1')
    event_data = {
        'event_type': 'send_message',
        'method_params': {'channel_id': 'channel1', 'thread_id': 'thread1', 'is_internal': True},
        'message_id': '123',
        'guid': 'test-guid'
    }

    # Initialize the internal_processing_tasks dictionary
    interaction_queue_manager.internal_processing_tasks = {queue_key: asyncio.create_task(asyncio.sleep(0))}

    # Add event to the internal queue
    await interaction_queue_manager.internal_queues[queue_key].put(event_data)

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

@pytest.mark.asyncio
async def test_clear_expired_messages_with_running_loop(interaction_queue_manager, mock_global_manager):
    # Set the backend_dispatcher explicitement
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher

    # Create a running event loop
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.is_running.return_value = True

        # APRÈS avoir configuré le mock de get_event_loop, on met en place le mock de clean_all_queues
        mock_global_manager.backend_internal_queue_processing_dispatcher.clean_all_queues = AsyncMock(return_value=5)

        # Call the method directly (sans initialize)
        interaction_queue_manager.clear_expired_messages()

        # Attendre un tick pour permettre à la tâche async de s'exécuter
        await asyncio.sleep(0)

        # Assert that clean_all_queues was scheduled
        mock_global_manager.backend_internal_queue_processing_dispatcher.clean_all_queues.assert_called_once()

@pytest.mark.asyncio
async def test_save_event_to_backend_json_error(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    # Create an event with non-serializable data
    event_data = {
        'message_id': '123',
        'guid': 'abc',
        'method_params': {'non_serializable': object()}
    }

    # Test that the error is caught and logged
    await interaction_queue_manager.save_event_to_backend(event_data, 'channel1', 'thread1')
    interaction_queue_manager.logger.error.assert_called()

@pytest.mark.asyncio
async def test_process_internal_queue_different_event_types(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.add_reaction = AsyncMock()

    # Set up necessaire
    interaction_queue_manager.user_interaction_dispatcher = dispatcher
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()

    queue_key = ('channel1', 'thread1')

    # Test add_reaction event avec message_id et guid
    event_data_add = {
        'event_type': 'add_reaction',
        'method_params': {'channel_id': 'channel1', 'thread_id': 'thread1', 'is_internal': True},
        'message_id': '123',
        'guid': 'test-guid'
    }

    # Initialize the processing tasks
    interaction_queue_manager.internal_processing_tasks = {queue_key: asyncio.create_task(asyncio.sleep(0))}

    # Add event to the internal queue
    await interaction_queue_manager.internal_queues[queue_key].put(event_data_add)

    # Attendre un tick
    await asyncio.sleep(0)

    # Run the processor
    await interaction_queue_manager.process_internal_queue(queue_key)

    # Assert the reaction was added
    dispatcher.add_reaction.assert_called_once_with(
        channel_id='channel1', thread_id='thread1', is_internal=True, is_replayed=True
    )

@pytest.mark.asyncio
async def test_process_external_reactions_batch(interaction_queue_manager, mock_global_manager):
    # Setup complet
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.update_reactions_batch = AsyncMock()
    interaction_queue_manager.user_interaction_dispatcher = dispatcher
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()

    queue_key = ('channel1', 'thread1')
    reactions_actions = [
        {
            'action': 'add',
            'reaction': {
                'event': {
                    'channel_id': 'channel1',
                    'thread_id': 'thread1',
                    'timestamp': '123456'
                }
            }
        }
    ]

    event_data = {
        'event_type': 'update_reactions_batch',
        'method_params': {
            'reactions_actions': reactions_actions,
            'is_internal': False
        },
        'message_id': '123456',
        'guid': 'test-guid'
    }

    await interaction_queue_manager.external_queues[queue_key].put(event_data)
    await interaction_queue_manager.process_external_queue(queue_key)

    # Verify batch update was called
    assert dispatcher.update_reactions_batch.called
    dispatcher.update_reactions_batch.assert_called_once_with(
        reactions_actions=reactions_actions,
        is_replayed=True
    )

@pytest.mark.asyncio
async def test_mark_event_processed_error_handling(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.dequeue_message = AsyncMock(side_effect=Exception("Test error"))

    event_data = {
        'message_id': '123',
        'guid': 'abc',
        'method_params': {'channel_id': 'channel1', 'thread_id': 'thread1'}
    }

    # Test that the error is caught and logged
    await interaction_queue_manager.mark_event_processed(event_data, internal=True)
    interaction_queue_manager.logger.error.assert_called()

def test_generate_unique_event_id(interaction_queue_manager):
    id1 = interaction_queue_manager.generate_unique_event_id()
    id2 = interaction_queue_manager.generate_unique_event_id()

    # Verify IDs are unique
    assert id1 != id2
    # Verify IDs are valid UUIDs
    assert len(id1) == 36
    assert len(id2) == 36

def test_make_serializable(interaction_queue_manager):
    # Test avec différents types de données simples
    test_data = {
        'str': 'test',
        'int': 123,
        'float': 123.45,
        'bool': True,
        'none': None,
        'list': [1, 2, 3],
        'dict': {'nested': 'dict'},
    }

    result = make_serializable(test_data)

    # Vérifications basiques
    assert result['str'] == 'test'
    assert result['int'] == 123
    assert result['float'] == 123.45
    assert result['bool'] is True
    assert result['none'] is None
    assert result['list'] == [1, 2, 3]
    assert result['dict'] == {'nested': 'dict'}

    # Vérifier que le résultat est JSON serializable
    serialized = json.dumps(result)
    assert isinstance(serialized, str)

@pytest.mark.asyncio
async def test_add_to_queue_with_reactions(interaction_queue_manager, mock_global_manager):
    # Fix: Initialize backend_dispatcher properly
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher = interaction_queue_manager.backend_dispatcher
    mock_backend_dispatcher.enqueue_message = AsyncMock()

    # Fix: Initialize required containers
    interaction_queue_manager.internal_event_container = MagicMock()
    interaction_queue_manager.external_event_container = MagicMock()

    reaction_event = {
        'channel_id': 'test_channel',
        'thread_id': 'test_thread',
        'timestamp': '123456'
    }

    method_params = {
        'reactions': [{
            'event': reaction_event,
            'reaction_type': 'thumbs_up'
        }],
        'is_internal': True
    }

    await interaction_queue_manager.add_to_queue('add_reactions', method_params)

    queue_key = ('test_channel', 'test_thread')
    assert not interaction_queue_manager.internal_queues[queue_key].empty()

    # Verify backend call was made
    mock_backend_dispatcher.enqueue_message.assert_called_once()

# Test error handling in mark_event_processed
@pytest.mark.asyncio
async def test_mark_event_processed_with_invalid_event(interaction_queue_manager, mock_global_manager):
    mock_backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    mock_backend_dispatcher.dequeue_message = AsyncMock()

    event_data = {
        'message_id': '123',
        'guid': 'test-guid',
        'method_params': {
            'event': {'invalid': 'data'},  # Invalid event data
            'channel_id': 'test_channel',
            'thread_id': 'test_thread'
        }
    }

    await interaction_queue_manager.mark_event_processed(event_data, internal=True)
    interaction_queue_manager.logger.error.assert_called()

@pytest.mark.asyncio
async def test_process_queue_with_message_type(interaction_queue_manager, mock_global_manager):
    # Setup complete dispatcher configuration
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()
    mock_enqueue = AsyncMock()
    interaction_queue_manager.backend_dispatcher.enqueue_message = mock_enqueue

    # Setup dispatcher with proper mocks
    dispatcher = mock_global_manager.user_interactions_dispatcher
    mock_send = AsyncMock()
    dispatcher.send_message = mock_send
    interaction_queue_manager.user_interaction_dispatcher = dispatcher

    # Initialize necessary containers
    interaction_queue_manager.internal_event_container = MagicMock()
    interaction_queue_manager.external_event_container = MagicMock()

    # Setup processing tasks dict and queue
    queue_key = ('channel1', 'thread1')
    if queue_key not in interaction_queue_manager.internal_queues:
        interaction_queue_manager.internal_queues[queue_key] = asyncio.Queue()

    # Create event data with TEXT message type
    event_data = {
        'event_type': 'send_message',
        'method_params': {
            'channel_id': 'channel1',
            'thread_id': 'thread1',
            'message_type': MessageType.TEXT,
            'is_internal': True,
            'content': 'test message'
        },
        'message_id': '123',
        'guid': 'test-guid'
    }

    # Set up initial task state
    interaction_queue_manager.internal_processing_tasks = {
        queue_key: asyncio.create_task(asyncio.sleep(0))
    }

    # Add to queue
    await interaction_queue_manager.internal_queues[queue_key].put(event_data)

    # Process the queue and wait for completion
    await interaction_queue_manager.process_internal_queue(queue_key)

    # Verify and await the async calls
    assert mock_send.called, "send_message was not called"
    await mock_send.wait_until_called()

    # Get and verify the call arguments
    call_args = mock_send.call_args
    assert call_args is not None

    kwargs = call_args.kwargs
    assert kwargs['channel_id'] == 'channel1'
    assert kwargs['thread_id'] == 'thread1'
    assert kwargs['is_internal'] is True
    assert kwargs['is_replayed'] is True
    assert kwargs['content'] == 'test message'
    assert isinstance(kwargs['message_type'], MessageType)
    assert kwargs['message_type'] == MessageType.TEXT

    # Clean up
    await interaction_queue_manager.internal_queues[queue_key].join()

@pytest.mark.asyncio
async def test_process_external_reactions_batch(interaction_queue_manager, mock_global_manager):
    # Fix: Initialize the external_reaction_tasks attribute
    interaction_queue_manager.external_reaction_tasks = {}

    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.add_reactions = AsyncMock()
    interaction_queue_manager.user_interaction_dispatcher = dispatcher

    # Set up backend dispatcher
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()

    event_data = {
        'event_type': 'add_reactions',
        'method_params': {
            'reactions': [{
                'event': {
                    'channel_id': 'test_channel',
                    'thread_id': 'test_thread',
                    'timestamp': '123456'
                },
                'reaction_type': 'thumbs_up'
            }],
            'is_internal': False
        },
        'message_id': '123456',
        'guid': 'test-guid'
    }

    queue_key = ('test_channel', 'test_thread')
    await interaction_queue_manager.external_queues[queue_key].put(event_data)
    await interaction_queue_manager.process_external_reactions(queue_key)

    # Verify reactions were processed
    dispatcher.add_reactions.assert_called_once()

@pytest.mark.asyncio
async def test_clear_expired_messages_without_running_loop(interaction_queue_manager, mock_global_manager):
    # Setup backend dispatcher with proper async mock
    mock_clean = AsyncMock(return_value=5)
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.backend_dispatcher.clean_all_queues = mock_clean

    with patch('asyncio.get_event_loop') as mock_loop:
        # Setup mock loop with proper async handling
        mock_loop_instance = MagicMock()
        mock_loop_instance.is_running.return_value = False

        async def run_until_complete_mock(coro):
            return await coro

        mock_loop_instance.run_until_complete = run_until_complete_mock
        mock_loop.return_value = mock_loop_instance

        # Run the method
        interaction_queue_manager.clear_expired_messages()

        # Wait for and verify the async call
        assert mock_clean.called
        await mock_clean.wait_until_called()

        # Verify correct number of calls
        assert mock_clean.call_count == 1

# Test serialization of complex objects
def test_make_serializable_with_custom_objects(interaction_queue_manager):
    class CustomObject:
        def __init__(self):
            self.value = "test"

    test_data = {
        'custom': CustomObject(),
        'nested': {
            'custom': CustomObject()
        },
        'list': [CustomObject(), CustomObject()]
    }

    result = make_serializable(test_data)

    # Verify all CustomObjects were converted to dicts
    assert isinstance(result['custom'], dict)
    assert result['custom']['value'] == "test"
    assert isinstance(result['nested']['custom'], dict)
    assert all(isinstance(x, dict) for x in result['list'])

# Test IncomingNotificationDataBase conversion
@pytest.mark.asyncio
async def test_process_queue_with_notification_data(interaction_queue_manager, mock_global_manager):
    dispatcher = mock_global_manager.user_interactions_dispatcher
    dispatcher.send_message = AsyncMock()
    interaction_queue_manager.user_interaction_dispatcher = dispatcher

    notification_data = {
        'channel_id': 'test_channel',
        'thread_id': 'test_thread',
        'timestamp': '123456'
    }

    event_data = {
        'event_type': 'send_message',
        'method_params': {
            'event': notification_data,
            'is_internal': True
        },
        'message_id': '123456',
        'guid': 'test-guid'
    }

    queue_key = ('test_channel', 'test_thread')
    await interaction_queue_manager.internal_queues[queue_key].put(event_data)
    await interaction_queue_manager.process_internal_queue(queue_key)

    # Verify event was converted to IncomingNotificationDataBase
    call_args = dispatcher.send_message.call_args[1]
    assert isinstance(call_args['event'], IncomingNotificationDataBase)

# Test queue processing termination
@pytest.mark.asyncio
async def test_queue_processing_termination(interaction_queue_manager):
    queue_key = ('channel1', 'thread1')

    # Create a processing task
    task = asyncio.create_task(interaction_queue_manager.process_internal_queue(queue_key))

    # Wait briefly
    await asyncio.sleep(0.1)

    # Verify task is removed when queue is empty
    assert queue_key not in interaction_queue_manager.internal_processing_tasks

    # Cancel task to clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

def initialize_queue_manager(interaction_queue_manager, mock_global_manager):
    """Helper function to properly initialize the queue manager for tests"""
    interaction_queue_manager.backend_dispatcher = mock_global_manager.backend_internal_queue_processing_dispatcher
    interaction_queue_manager.user_interaction_dispatcher = mock_global_manager.user_interactions_dispatcher
    interaction_queue_manager.internal_event_container = MagicMock()
    interaction_queue_manager.external_event_container = MagicMock()
    interaction_queue_manager.external_reaction_tasks = {}
    interaction_queue_manager.backend_dispatcher.dequeue_message = AsyncMock()
    interaction_queue_manager.backend_dispatcher.enqueue_message = AsyncMock()
    return interaction_queue_manager
