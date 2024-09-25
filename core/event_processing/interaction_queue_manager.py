import asyncio
import json
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)

from core.event_processing.queued_interaction import QueuedInteraction

class InteractionQueueManager:
    def __init__(self, backend_dispatcher, user_interaction_dispatcher, logger):
        self.queue = asyncio.Queue()  # Queue to manage events in memory
        self.backend_dispatcher: BackendInternalDataProcessingDispatcher = backend_dispatcher
        self.user_interaction_dispatcher: UserInteractionsDispatcher = user_interaction_dispatcher
        self.logger = logger

        # Start processing events in the queue
        asyncio.create_task(self.process_queue())

    async def add_to_queue(self, event_type: str, event: dict, **kwargs):
        """Encapsulate and add an event to the queue and backend"""
        queued_interaction = QueuedInteraction(event_type, event, **kwargs)

        # Save the encapsulated event in the backend
        await self.save_event_to_backend(queued_interaction)

        # Add the event to the in-memory queue for processing
        await self.queue.put(queued_interaction)
        self.logger.info(f"Added {event_type} to queue for event: {event}")

    async def save_event_to_backend(self, interaction: QueuedInteraction):
        """Save the encapsulated event in the backend"""
        event = interaction.event
        channel_id = event.get('channel_id', 'default_channel')
        thread_id = event.get('thread_id', 'default_thread')
        message_id = event.get('timestamp', 'default_timestamp')

        # Convert the interaction to JSON for storage
        event_json = json.dumps(interaction.to_dict())

        # Use the dispatcher to enqueue the interaction in the backend
        await self.backend_dispatcher.enqueue_message(
            channel_id=channel_id,
            thread_id=thread_id,
            message_id=message_id,
            message=event_json
        )
        self.logger.info(f"Event saved to backend: {channel_id}/{thread_id} - {message_id}")

    async def load_events_from_backend(self):
        """Load all unprocessed events from the backend"""
        channel_id = "default_channel"
        thread_id = "default_thread"

        # Use the dispatcher to retrieve all pending messages
        messages = await self.backend_dispatcher.get_all_messages(channel_id, thread_id)

        # Add the messages to the local queue for processing in order
        for message in messages:
            event_data = json.loads(message)
            queued_interaction = QueuedInteraction.from_dict(event_data)
            await self.queue.put(queued_interaction)
            self.logger.info(f"Loaded event from backend: {event_data}")

    async def process_queue(self):
        """Process events from the queue one by one"""
        while True:
            queued_interaction: QueuedInteraction = await self.queue.get()

            try:
                # Call the appropriate function based on event type
                event_type = queued_interaction.event_type
                params = queued_interaction.params

                if event_type == "send_message":
                    await self.user_interaction_dispatcher.send_message(**params)
                elif event_type == "add_reaction":
                    await self.user_interaction_dispatcher.add_reaction(**params)
                elif event_type == "remove_reaction":
                    await self.user_interaction_dispatcher.remove_reaction(**params)

                # After processing, mark the event as processed
                await self.mark_event_processed(queued_interaction)
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
            finally:
                self.queue.task_done()

    async def mark_event_processed(self, interaction: QueuedInteraction):
        """Mark an event as processed by removing it from the backend"""
        event = interaction.event
        channel_id = event.get('channel_id', 'default_channel')
        thread_id = event.get('thread_id', 'default_thread')
        message_id = event.get('timestamp', 'default_timestamp')

        # Use the dispatcher to dequeue the message from the backend
        await self.backend_dispatcher.dequeue_message(channel_id, thread_id, message_id)
        self.logger.info(f"Event dequeued from backend: {channel_id}/{thread_id} - {message_id}")
