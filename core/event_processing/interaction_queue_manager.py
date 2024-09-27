import asyncio
import json
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)

class InteractionQueueManager:
    def __init__(self, global_manager):
        """
        Initialize the manager with the global manager reference.
        """
        # Set references from the global manager
        self.global_manager = global_manager
        self.backend_dispatcher: BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.user_interaction_dispatcher: UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        
        # Use the logger from the global manager for consistent logging
        self.logger = self.global_manager.logger

        # Queue to manage events in memory
        self.queue = asyncio.Queue()

        # Event container will be set in the initialize method
        self.event_container = None

    def initialize(self):
        """
        Initializes the event container and starts the event queue processing task.
        """
        # Set the event container from the backend dispatcher
        self.event_container = self.backend_dispatcher.events_queue
        
        # Log container initialization
        self.logger.info(f"Event container initialized: {self.event_container}")

        # Start the task to process the queue asynchronously
        asyncio.create_task(self.process_queue())
        self.logger.info("Queue processing task started.")

    async def add_to_queue(self, event_type: str, method_params: dict, **kwargs):
        """
        Add an event to the queue, storing the method parameters and any additional arguments.
        """
        event_data = {
            "event_type": event_type,
            "method_params": method_params,  # Store method parameters
            **kwargs  # Additional parameters (e.g., event metadata)
        }

        # Save the event in the backend
        await self.save_event_to_backend(event_data)

        # Add the event to the in-memory queue for processing
        await self.queue.put(event_data)
        self.logger.info(f"Added {event_type} to queue with params: {method_params}")

    async def save_event_to_backend(self, event_data: dict):
        """
        Save the event (along with method parameters) in the backend using the dispatcher.
        """
        channel_id = event_data.get('channel_id', 'default_channel')
        thread_id = event_data.get('thread_id', 'default_thread')
        message_id = event_data.get('timestamp', 'default_timestamp')

        # Convert the event to JSON for storage
        message_json = json.dumps(event_data)

        # Use the dispatcher to enqueue the message in the backend
        await self.backend_dispatcher.enqueue_message(
            data_container=self.event_container,  # Use the event container
            channel_id=channel_id, 
            thread_id=thread_id, 
            message_id=message_id, 
            message=message_json
        )
        self.logger.info(f"Event saved to backend: {channel_id}/{thread_id} - {message_id}")

    async def load_events_from_backend(self):
        """
        Load all unprocessed events from the backend and requeue them for processing.
        """
        channel_id = "default_channel"
        thread_id = "default_thread"

        # Use the dispatcher to retrieve all pending messages
        messages = await self.backend_dispatcher.get_all_messages(
            data_container=self.event_container,  # Use the event container
            channel_id=channel_id,
            thread_id=thread_id
        )

        # Add the messages to the local queue for processing in order
        for message in messages:
            event_data = json.loads(message)
            await self.queue.put(event_data)
            self.logger.info(f"Loaded event from backend: {event_data}")

    async def process_queue(self):
        """
        Process events from the queue one by one by replaying the method with the stored parameters.
        """
        while True:
            event_data = await self.queue.get()

            try:
                event_type = event_data['event_type']  # The type of method to be called
                method_params = event_data['method_params']  # The stored parameters for the method call

                # Replay the stored method with the appropriate parameters
                if event_type == "send_message":
                    await self.user_interaction_dispatcher.send_message(**method_params)
                elif event_type == "add_reaction":
                    await self.user_interaction_dispatcher.add_reaction(**method_params)
                elif event_type == "remove_reaction":
                    await self.user_interaction_dispatcher.remove_reaction(**method_params)

                # After processing, remove the message from the backend
                await self.mark_event_processed(event_data)
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
            finally:
                self.queue.task_done()

    async def mark_event_processed(self, event_data: dict):
        """
        Mark an event as processed by removing it from the backend.
        """
        channel_id = event_data.get('channel_id', 'default_channel')
        thread_id = event_data.get('thread_id', 'default_thread')
        message_id = event_data.get('timestamp', 'default_timestamp')

        # Use the dispatcher to dequeue the message from the backend
        await self.backend_dispatcher.dequeue_message(
            data_container=self.event_container,  # Use the event container
            channel_id=channel_id,
            thread_id=thread_id,
            message_id=message_id
        )
        self.logger.info(f"Event dequeued from backend: {channel_id}/{thread_id} - {message_id}")
