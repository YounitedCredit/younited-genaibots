import asyncio
import json
import uuid
from collections import defaultdict

from core.backend.backend_internal_queue_processing_dispatcher import (
    BackendInternalQueueProcessingDispatcher,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
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

        # Use the logger from the global manager for consistent logging
        self.logger = self.global_manager.logger

        # Queues per channel/thread for internal and external events
        self.internal_queues = defaultdict(asyncio.Queue)
        self.external_queues = defaultdict(asyncio.Queue)

        # Event containers will be set in the initialize method
        self.internal_event_container = None
        self.external_event_container = None

        # Track processing tasks to avoid duplicate tasks per queue_key
        self.internal_processing_tasks = {}
        self.external_processing_tasks = {}

    def initialize(self):
        """
        Initializes the event containers.
        """
        # Set the event containers for internal and external events from the backend dispatcher
        self.backend_dispatcher: BackendInternalQueueProcessingDispatcher = self.global_manager.backend_internal_queue_processing_dispatcher
        self.user_interaction_dispatcher: UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        self.internal_event_container = self.backend_dispatcher.internal_events_queue
        self.external_event_container = self.backend_dispatcher.external_events_queue

        # Log container initialization
        self.logger.debug(f"Internal event container initialized: {self.internal_event_container}")
        self.logger.debug(f"External event container initialized: {self.external_event_container}")

        self.logger.info("InteractionQueueManager initialized.")

    def generate_unique_event_id(self):
        """
        Generate a unique event identifier using a UUID.
        """
        return str(uuid.uuid4())

    async def add_to_queue(self, event_type: str, method_params: dict, **kwargs):
        """
        Add an event to the appropriate queue based on the is_internal flag.
        """
        # Generate a unique event identifier
        event_id = self.generate_unique_event_id()

        # Extract channel_id, thread_id, and timestamp to determine the queue
        channel_id = method_params.get('channel_id')
        thread_id = method_params.get('thread_id')
        message_id = method_params.get('timestamp')

        # If any of these are None, try to get them from 'event' in 'method_params'
        if not channel_id or not thread_id or not message_id:
            event = method_params.get('event')
            if event:
                if isinstance(event, IncomingNotificationDataBase):
                    channel_id = channel_id or event.channel_id
                    thread_id = thread_id or event.thread_id
                    message_id = message_id or event.timestamp
                elif isinstance(event, dict):
                    channel_id = channel_id or event.get('channel_id')
                    thread_id = thread_id or event.get('thread_id')
                    message_id = message_id or event.get('timestamp')

        # Set default values if still None
        channel_id = channel_id or 'default_channel'
        thread_id = thread_id or 'default_thread'
        message_id = message_id or 'default_timestamp'

        # Construct full_message_id and store it in event_data
        full_message_id = f"{channel_id}_{thread_id}_{message_id}_{event_id}"

        # Store the event_id in event_data for easy reference
        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "method_params": method_params,  # Store method parameters
            "full_message_id": full_message_id,
            **kwargs  # Additional parameters (e.g., event metadata)
        }

        # Save the event in the backend with a unique identifier
        await self.save_event_to_backend(event_data, channel_id, thread_id)

        # Create queue key
        queue_key = (channel_id, thread_id)

        # Check if the event is internal or external and add to the appropriate queue
        is_internal = method_params.get('is_internal', False)
        if is_internal:
            await self.internal_queues[queue_key].put(event_data)
            self.logger.debug(f"Added {event_type} to internal queue {queue_key} with params: {method_params}")

            # Start processing task if not already running
            if queue_key not in self.internal_processing_tasks:
                self.internal_processing_tasks[queue_key] = asyncio.create_task(self.process_internal_queue(queue_key))
        else:
            await self.external_queues[queue_key].put(event_data)
            self.logger.debug(f"Added {event_type} to external queue {queue_key} with params: {method_params}")

            # Start processing task if not already running
            if queue_key not in self.external_processing_tasks:
                self.external_processing_tasks[queue_key] = asyncio.create_task(self.process_external_queue(queue_key))

    async def save_event_to_backend(self, event_data: dict, channel_id, thread_id):
        """
        Save the event (along with method parameters) in the backend using the appropriate dispatcher.
        """
        try:
            # Use the event_id to ensure uniqueness
            full_message_id = event_data['full_message_id']

            # Convert event_data to JSON for storage
            message_json = json.dumps(event_data)

            # Determine if the event is internal or external
            is_internal = event_data.get('method_params', {}).get('is_internal', False)
            container = self.internal_event_container if is_internal else self.external_event_container

            # Use the dispatcher to enqueue the message in the backend with a unique event_id
            await self.backend_dispatcher.enqueue_message(
                data_container=container,
                channel_id=channel_id,
                thread_id=thread_id,
                message_id=full_message_id,  # Use full_message_id
                message=message_json
            )
            self.logger.debug(f"Event saved to backend: {channel_id}/{thread_id} - {full_message_id}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to encode event data to JSON: {e}")

        except AttributeError as e:
            self.logger.error(f"Attribute error: {e}")

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")

    async def process_internal_queue(self, queue_key):
        """
        Process events from the internal queue for a specific channel/thread.
        """
        try:
            while True:
                event_data = await self.internal_queues[queue_key].get()

                try:
                    event_type = event_data['event_type']  # The type of method to be called
                    method_params = event_data['method_params']  # The stored parameters for the method call

                    # Rebuild the event object from the stored dictionary
                    if 'event' in method_params:
                        event_dict = method_params['event']
                        method_params['event'] = IncomingNotificationDataBase.from_dict(event_dict)

                    # Rebuild MessageType from string if it exists
                    if 'message_type' in method_params:
                        method_params['message_type'] = MessageType(method_params['message_type'])

                    # Use the user_interaction_dispatcher to replay the methods
                    dispatcher = self.user_interaction_dispatcher

                    # Replay the stored method with the appropriate parameters
                    if event_type == "send_message":
                        await dispatcher.send_message(**method_params, is_replayed=True)
                    elif event_type == "upload_file":
                        await dispatcher.upload_file(**method_params, is_replayed=True)
                    elif event_type == "add_reaction":
                        await dispatcher.add_reaction(**method_params, is_replayed=True)
                    elif event_type == "remove_reaction":
                        await dispatcher.remove_reaction(**method_params, is_replayed=True)
                    elif event_type == "remove_reaction_from_thread":  # New case for removing reactions from thread
                        await dispatcher.remove_reaction_from_thread(**method_params, is_replayed=True)

                    # After processing, remove the message from the backend
                    await self.mark_event_processed(event_data, internal=True)
                except Exception as e:
                    self.logger.error(f"Error processing internal event: {e}")
                finally:
                    # Mark task as done to avoid re-processing
                    self.internal_queues[queue_key].task_done()

                # If the queue is empty, remove the task
                if self.internal_queues[queue_key].empty():
                    break
        finally:
            # Remove the task from tracking
            del self.internal_processing_tasks[queue_key]

    async def process_external_queue(self, queue_key):
        """
        Process events from the external queue for a specific channel/thread.
        """
        try:
            while True:
                event_data = await self.external_queues[queue_key].get()

                try:
                    event_type = event_data['event_type']  # The type of method to be called
                    method_params = event_data['method_params']  # The stored parameters for the method call

                    # Rebuild the event object from the stored dictionary
                    if 'event' in method_params:
                        event_dict = method_params['event']
                        method_params['event'] = IncomingNotificationDataBase.from_dict(event_dict)

                    # Rebuild MessageType from string if it exists
                    if 'message_type' in method_params:
                        method_params['message_type'] = MessageType(method_params['message_type'])

                    # Use the user_interaction_dispatcher to replay the methods
                    dispatcher = self.user_interaction_dispatcher

                    # Replay the stored method with the appropriate parameters
                    if event_type == "send_message":
                        await dispatcher.send_message(**method_params, is_replayed=True)
                    elif event_type == "upload_file":
                        await dispatcher.upload_file(**method_params, is_replayed=True)
                    elif event_type == "add_reaction":
                        await dispatcher.add_reaction(**method_params, is_replayed=True)
                    elif event_type == "remove_reaction":
                        await dispatcher.remove_reaction(**method_params, is_replayed=True)
                    elif event_type == "remove_reaction_from_thread":  # New case for removing reactions from thread
                        await dispatcher.remove_reaction_from_thread(**method_params, is_replayed=True)

                    # After processing, remove the message from the backend
                    await self.mark_event_processed(event_data, internal=False)
                except Exception as e:
                    self.logger.error(f"Error processing external event: {e}")
                finally:
                    # Mark task as done to avoid re-processing
                    self.external_queues[queue_key].task_done()

                # If the queue is empty, remove the task
                if self.external_queues[queue_key].empty():
                    break
        finally:
            # Remove the task from tracking
            del self.external_processing_tasks[queue_key]

    async def mark_event_processed(self, event_data: dict, internal: bool):
        """
        Mark an event as processed by removing it from the backend.
        """
        try:
            # Use full_message_id
            full_message_id = event_data['full_message_id']
            method_params = event_data.get('method_params', {})
            event = method_params.get('event', {})

            # Check if the event object is an instance of IncomingNotificationDataBase
            if isinstance(event, IncomingNotificationDataBase):
                channel_id = event.channel_id
                thread_id = event.thread_id
            else:
                # If event is a dictionary or None, retrieve values from method_params or use default values
                channel_id = method_params.get('channel_id', 'default_channel')
                thread_id = method_params.get('thread_id', 'default_thread')

            container = self.internal_event_container if internal else self.external_event_container

            # Use the dispatcher to dequeue the message from the backend
            await self.backend_dispatcher.dequeue_message(
                data_container=container,
                channel_id=channel_id,
                thread_id=thread_id,
                message_id=full_message_id  # Ensure we dequeue the exact unique message
            )
            self.logger.debug(f"Event dequeued from backend: {channel_id}/{thread_id} - {full_message_id}")

        except Exception as e:
            self.logger.error(f"Error marking event as processed: {e}")
