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
from utils.config_manager.config_model import BotConfig


class InteractionQueueManager:
    def __init__(self, global_manager):
        """
        Initialize the InteractionQueueManager with references from the global manager.
        """
        # Set references from the global manager
        self.global_manager = global_manager
        self.logger = self.global_manager.logger

        # Queues for internal and external events per channel/thread
        self.internal_queues = defaultdict(asyncio.Queue)
        self.external_queues = defaultdict(asyncio.Queue)

        # Containers for events, initialized later
        self.internal_event_container = None
        self.external_event_container = None

        # Track processing tasks to avoid duplicate processing per queue_key
        self.internal_processing_tasks = {}
        self.external_processing_tasks = {}

    def initialize(self):
        """
        Initialize event containers and log the setup.
        """
        # Set the event containers for internal and external events from the backend dispatcher
        self.backend_dispatcher: BackendInternalQueueProcessingDispatcher = self.global_manager.backend_internal_queue_processing_dispatcher
        self.user_interaction_dispatcher: UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher

        # Assign event containers and TTLs
        self.internal_event_container = self.backend_dispatcher.internal_events_queue
        self.internal_queue_ttl = self.backend_dispatcher.internal_events_queue_ttl
        self.external_event_container = self.backend_dispatcher.external_events_queue
        self.external_queues_ttl = self.backend_dispatcher.external_events_queue_ttl
        self.messages_queue_container = self.backend_dispatcher.messages_queue
        self.messages_queue_ttl = self.backend_dispatcher.messages_queue_ttl
        self.wait_queue_container = self.backend_dispatcher.wait_queue
        self.wait_queue_ttl = self.backend_dispatcher.wait_queue_ttl
        self.bot_config: BotConfig = self.global_manager.bot_config

        # Log container initialization
        self.logger.debug(f"Internal event container initialized: {self.internal_event_container}")
        self.logger.debug(f"External event container initialized: {self.external_event_container}")

        self.logger.info("InteractionQueueManager initialized.")
        self.clear_expired_messages()

    def clear_expired_messages(self):
        """
        Synchronously clear expired messages across all queues.
        """
        try:
            loop = asyncio.get_event_loop()

            if loop.is_running():
                self.logger.info("Event loop is running. Scheduling asynchronous cleanup of expired messages.")
                asyncio.create_task(self.backend_dispatcher.clean_all_queues())
            else:
                self.logger.info("Running synchronous cleanup of expired messages.")
                expired_count = loop.run_until_complete(self.backend_dispatcher.clean_all_queues())
                self.logger.info(f"Removed {expired_count} expired messages from the queues.")
        except Exception as e:
            self.logger.error(f"Failed to clean expired messages from queues: {str(e)}")

    def generate_unique_event_id(self):
        """
        Generate a unique event identifier using a UUID.
        """
        return str(uuid.uuid4())

    async def add_to_queue(self, event_type: str, method_params: dict, **kwargs):
        """
        Add an event to the appropriate queue based on the is_internal flag, with a unique GUID.
        """
        # Generate a unique GUID for the event
        guid = self.generate_unique_event_id()

        # Extract channel_id, thread_id, and timestamp to determine the queue
        channel_id = method_params.get('channel_id')
        thread_id = method_params.get('thread_id')
        message_id = method_params.get('message_id')
        self.logger.debug(f"Initial channel_id: {channel_id}, thread_id: {thread_id}, message_id: {message_id}")

        # If one of the fields is missing, try to extract them from 'event' in 'method_params'
        if not channel_id or not thread_id or not message_id:
            event = method_params.get('event')
            if event:
                self.logger.debug(f"Event found in method_params: {event}")
                if isinstance(event, IncomingNotificationDataBase):
                    channel_id = channel_id or event.channel_id
                    thread_id = thread_id or event.thread_id
                    message_id = message_id or event.timestamp
                elif isinstance(event, dict):
                    channel_id = channel_id or event.get('channel_id')
                    thread_id = thread_id or event.get('thread_id')
                    message_id = message_id or event.get('timestamp')
                self.logger.debug(f"Extracted channel_id: {channel_id}, thread_id: {thread_id}, message_id: {message_id}")

        # Set default values if they are still None
        channel_id = channel_id or 'default_channel'
        thread_id = thread_id or 'default_thread'

        # Continue with the rest of the code if message_id is not None
        message_id = message_id

        # Construct the full_message_id using the GUID for uniqueness
        full_message_id = f"{channel_id}_{thread_id}_{message_id}_{guid}"

        # Store the GUID in event_data for easy reference
        event_data = {
            "guid": guid,
            "event_type": event_type,
            "method_params": method_params,  # Store the method parameters
            "full_message_id": full_message_id,
            "message_id": message_id,
            **kwargs  # Additional parameters (e.g., event metadata)
        }

        # Log the event with GUID for debugging purposes
        self.logger.debug(f"Adding {event_type} with GUID {guid} to queue {channel_id}_{thread_id}")

        # Save the event in the backend with a unique identifier
        await self.save_event_to_backend(event_data, channel_id, thread_id)

        # Create the queue key
        queue_key = (channel_id, thread_id)

        # Determine if the event is internal or external and add it to the appropriate queue
        is_internal = method_params.get('is_internal', False)
        if is_internal:
            await self.internal_queues[queue_key].put(event_data)
            self.logger.debug(f"Added {event_type} to internal queue {queue_key} with params: {method_params}")

            # Start the processing task if it is not already running
            if queue_key not in self.internal_processing_tasks:
                self.internal_processing_tasks[queue_key] = asyncio.create_task(self.process_internal_queue(queue_key))
        else:
            await self.external_queues[queue_key].put(event_data)
            self.logger.debug(f"Added {event_type} to external queue {queue_key} with params: {method_params}")

            # Start the processing task if it is not already running
            if queue_key not in self.external_processing_tasks:
                self.external_processing_tasks[queue_key] = asyncio.create_task(self.process_external_queue(queue_key))

    async def save_event_to_backend(self, event_data: dict, channel_id, thread_id):
        """
        Save the event (along with method parameters) in the backend using the appropriate dispatcher.
        """
        try:
            # Extraire le GUID et le message_id
            message_id = event_data['message_id']
            guid = event_data['guid']  # GUID déjà généré dans add_to_queue
            message_json = json.dumps(event_data)

            # Déterminer si l'événement est interne ou externe
            is_internal = event_data.get('method_params', {}).get('is_internal', False)
            container = self.internal_event_container if is_internal else self.external_event_container

            # Sauvegarder l'événement dans le backend
            await self.backend_dispatcher.enqueue_message(
                data_container=container,
                channel_id=channel_id,
                thread_id=thread_id,
                message_id=message_id,
                message=message_json,
                guid=guid  # GUID utilisé ici
            )
            self.logger.debug(f"Event saved to backend: {channel_id}/{thread_id} - {message_id}_{guid}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to encode event data to JSON: {e}")
        except AttributeError as e:
            self.logger.error(f"Attribute error: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")

    async def mark_event_processed(self, event_data: dict, internal: bool):
        """
        Mark an event as processed by removing it from the backend using the GUID.
        """
        try:
            message_id = event_data['message_id']
            guid = event_data['guid']  # GUID stocké dans event_data
            method_params = event_data.get('method_params', {})
            event = method_params.get('event', {})

            # Déterminer channel_id et thread_id
            if isinstance(event, IncomingNotificationDataBase):
                channel_id = event.channel_id
                thread_id = event.thread_id
            else:
                channel_id = method_params.get('channel_id', 'default_channel')
                thread_id = method_params.get('thread_id', 'default_thread')

            container = self.internal_event_container if internal else self.external_event_container

            # Utiliser le dispatcher pour supprimer le message du backend
            await self.backend_dispatcher.dequeue_message(
                data_container=container,
                channel_id=channel_id,
                thread_id=thread_id,
                message_id=message_id,
                guid=guid  # GUID utilisé ici
            )
            self.logger.debug(f"Event dequeued from backend: {channel_id}/{thread_id} - {message_id}_{guid}")

        except Exception as e:
            self.logger.error(f"Error marking event as processed: {e}")

    async def process_internal_queue(self, queue_key):
        """
        Process events from the internal queue for a specific channel/thread.
        """
        try:
            while True:
                event_data = await self.internal_queues[queue_key].get()

                try:
                    event_type = event_data['event_type']
                    method_params = event_data['method_params']

                    # Rebuild the event object from the stored dictionary
                    if 'event' in method_params:
                        event_dict = method_params['event']
                        method_params['event'] = IncomingNotificationDataBase.from_dict(event_dict)

                    if 'message_type' in method_params:
                        method_params['message_type'] = MessageType(method_params['message_type'])

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
                    elif event_type == "remove_reaction_from_thread":
                        await dispatcher.remove_reaction_from_thread(**method_params, is_replayed=True)

                    # Mark the event as processed and remove it from the backend
                    await self.mark_event_processed(event_data, internal=True)
                except Exception as e:
                    self.logger.error(f"Error processing internal event: {e}")
                finally:
                    self.internal_queues[queue_key].task_done()

                if self.internal_queues[queue_key].empty():
                    break
        finally:
            del self.internal_processing_tasks[queue_key]

    async def process_external_queue(self, queue_key):
        """
        Process events from the external queue for a specific channel/thread.
        """
        try:
            while True:
                event_data = await self.external_queues[queue_key].get()

                try:
                    event_type = event_data['event_type']
                    method_params = event_data['method_params']

                    # Rebuild the event object from the stored dictionary
                    if 'event' in method_params:
                        event_dict = method_params['event']
                        method_params['event'] = IncomingNotificationDataBase.from_dict(event_dict)

                    if 'message_type' in method_params:
                        method_params['message_type'] = MessageType(method_params['message_type'])

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
                    elif event_type == "remove_reaction_from_thread":
                        await dispatcher.remove_reaction_from_thread(**method_params, is_replayed=True)

                    # Mark the event as processed and remove it from the backend
                    await self.mark_event_processed(event_data, internal=False)
                except Exception as e:
                    self.logger.error(f"Error processing external event: {e}")
                finally:
                    self.external_queues[queue_key].task_done()

                if self.external_queues[queue_key].empty():
                    break
        finally:
            del self.external_processing_tasks[queue_key]
