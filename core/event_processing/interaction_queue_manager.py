import asyncio
import json
import uuid
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType

class InteractionQueueManager:
    def __init__(self, global_manager):
        """
        Initialize the manager with the global manager reference.
        """
        # Set references from the global manager
        self.global_manager = global_manager

        # Use the logger from the global manager for consistent logging
        self.logger = self.global_manager.logger

        # Two queues: one for internal events, one for external
        self.internal_queue = asyncio.Queue()
        self.external_queue = asyncio.Queue()

        # Event containers will be set in the initialize method
        self.internal_event_container = None
        self.external_event_container = None

    def initialize(self):
        """
        Initializes the event containers and starts the event queue processing tasks.
        """
        # Set the event containers for internal and external events from the backend dispatcher        
        self.backend_dispatcher: BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.user_interaction_dispatcher: UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        self.internal_event_container = self.backend_dispatcher.internal_events_queue
        self.external_event_container = self.backend_dispatcher.external_events_queue

        # Log container initialization
        self.logger.debug(f"Internal event container initialized: {self.internal_event_container}")
        self.logger.debug(f"External event container initialized: {self.external_event_container}")

        # Start the tasks to process the queues asynchronously
        asyncio.create_task(self.process_internal_queue())
        asyncio.create_task(self.process_external_queue())
        self.logger.info("Internal and external queue processing tasks started.")

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

        # Store the event_id in event_data for easy reference
        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "method_params": method_params,  # Store method parameters
            **kwargs  # Additional parameters (e.g., event metadata)
        }

        # Save the event in the backend with a unique identifier
        await self.save_event_to_backend(event_data)

        # Check if the event is internal or external and add to the appropriate queue
        is_internal = method_params.get('is_internal', False)
        if is_internal:
            await self.internal_queue.put(event_data)
            self.logger.debug(f"Added {event_type} to internal queue with params: {method_params}")
        else:
            await self.external_queue.put(event_data)
            self.logger.debug(f"Added {event_type} to external queue with params: {method_params}")

    async def save_event_to_backend(self, event_data: dict):
        """
        Save the event (along with method parameters) in the backend using the appropriate dispatcher.
        """
        try:
            # Extract method_params (method parameters) from event_data
            method_params = event_data.get('method_params', {})
            
            # Extract event object from method_params if present
            event = method_params.get('event', {})

            # Retrieve channel_id, thread_id, and timestamp from method_params or event
            channel_id = method_params.get('channel_id') or event.get('channel_id', 'default_channel')
            thread_id = method_params.get('thread_id') or event.get('thread_id', 'default_thread')
            message_id = method_params.get('timestamp') or event.get('timestamp', 'default_timestamp')

            # Use the event_id to ensure uniqueness
            event_id = event_data.get('event_id', 'default_event_id')

            # Convert event_data to JSON for storage
            message_json = json.dumps(event_data)

            # Determine if the event is internal or external
            is_internal = method_params.get('is_internal', False)
            container = self.internal_event_container if is_internal else self.external_event_container

            # Use the dispatcher to enqueue the message in the backend with a unique event_id
            await self.backend_dispatcher.enqueue_message(
                data_container=container,  # Use the correct container
                channel_id=channel_id, 
                thread_id=thread_id, 
                message_id=f"{message_id}_{event_id}",  # Append event_id to ensure uniqueness
                message=message_json
            )
            self.logger.debug(f"Event saved to backend: {channel_id}/{thread_id} - {message_id}_{event_id}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to encode event data to JSON: {e}")
        
        except AttributeError as e:
            self.logger.error(f"Attribute error: {e}")
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")

    async def load_events_from_backend(self):
        """
        Load all unprocessed events from the backend and requeue them for processing.
        """
        channel_id = "default_channel"
        thread_id = "default_thread"

        # Use the dispatcher to retrieve all pending messages for internal and external containers
        internal_messages = await self.backend_dispatcher.get_all_messages(
            data_container=self.internal_event_container,  # Use the internal event container
            channel_id=channel_id,
            thread_id=thread_id
        )

        external_messages = await self.backend_dispatcher.get_all_messages(
            data_container=self.external_event_container,  # Use the external event container
            channel_id=channel_id,
            thread_id=thread_id
        )

        # Add the messages to the local queues for processing in order
        for message in internal_messages:
            event_data = json.loads(message)
            await self.internal_queue.put(event_data)
            self.logger.debug(f"Loaded internal event from backend: {event_data}")

        for message in external_messages:
            event_data = json.loads(message)
            await self.external_queue.put(event_data)
            self.logger.debug(f"Loaded external event from backend: {event_data}")

    async def process_internal_queue(self):
        """
        Process events from the internal queue one by one by replaying the method with the stored parameters.
        """
        while True:
            event_data = await self.internal_queue.get()

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
                self.internal_queue.task_done()

    async def process_external_queue(self):
        """
        Process events from the external queue one by one by replaying the method with the stored parameters.
        """
        while True:
            event_data = await self.external_queue.get()

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
                self.external_queue.task_done()

    async def mark_event_processed(self, event_data: dict, internal: bool):
        """
        Mark an event as processed by removing it from the backend.
        """
        try:
            # Extract parameters from method_params
            method_params = event_data.get('method_params', {})
            event = method_params.get('event', {})

            # Check if the event object is an instance of IncomingNotificationDataBase
            if isinstance(event, IncomingNotificationDataBase):
                channel_id = event.channel_id
                thread_id = event.thread_id
                message_id = event.timestamp
            else:
                # If event is a dictionary or None, retrieve values from method_params or use default values
                channel_id = method_params.get('channel_id', 'default_channel')
                thread_id = method_params.get('thread_id', 'default_thread')
                message_id = method_params.get('timestamp', 'default_timestamp')

            # Append event_id to the message_id to ensure uniqueness
            event_id = event_data.get('event_id', 'default_event_id')
            container = self.internal_event_container if internal else self.external_event_container

            # Use the dispatcher to dequeue the message from the backend
            await self.backend_dispatcher.dequeue_message(
                data_container=container, 
                channel_id=channel_id,
                thread_id=thread_id,
                message_id=f"{message_id}_{event_id}"  # Ensure we dequeue the exact unique message
            )
            self.logger.debug(f"Event dequeued from backend: {channel_id}/{thread_id} - {message_id}_{event_id}")
        
        except Exception as e:
            self.logger.error(f"Error marking event as processed: {e}")
