from datetime import datetime, timedelta
from typing import List, Optional
import uuid
from azure.core.exceptions import ServiceRequestError, ServiceResponseError
from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from pydantic import BaseModel

from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.global_manager import GlobalManager
from utils.plugin_manager.plugin_manager import PluginManager

class AzureServiceBusConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_SERVICE_BUS_CONNECTION_STRING: str
    SERVICE_BUS_MESSAGES_QUEUE: str
    SERVICE_BUS_INTERNAL_EVENTS_QUEUE: str
    SERVICE_BUS_EXTERNAL_EVENTS_QUEUE: str
    SERVICE_BUS_WAIT_QUEUE: str

    # TTL configurations
    SERVICE_BUS_MESSAGES_QUEUE_TTL: Optional[int] = None  # in seconds
    SERVICE_BUS_INTERNAL_EVENTS_QUEUE_TTL: Optional[int] = None  # in seconds
    SERVICE_BUS_EXTERNAL_EVENTS_QUEUE_TTL: Optional[int] = None  # in seconds
    SERVICE_BUS_WAIT_QUEUE_TTL: Optional[int] = None  # in seconds


class AzureServiceBusQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.logger = global_manager.logger
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        config_dict = global_manager.config_manager.config_model.PLUGINS.BACKEND.INTERNAL_DATA_PROCESSING["AZURE_SERVICE_BUS"]
        self.service_bus_config = AzureServiceBusConfig(**config_dict)

        self.service_bus_client = None

    def initialize(self):
        try:
            self.service_bus_client = ServiceBusClient.from_connection_string(self.service_bus_config.AZURE_SERVICE_BUS_CONNECTION_STRING)
            self.logger.info("Azure Service Bus initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure Service Bus: {str(e)}")
            raise

    def apply_message_ttl(self, message: ServiceBusMessage, queue_ttl: Optional[int]):
        """
        Apply TTL to a ServiceBus message by setting its `time_to_live` property.
        """
        if queue_ttl:
            message.time_to_live = timedelta(seconds=queue_ttl)
            self.logger.info(f"Applied TTL of {queue_ttl} seconds to message.")

    async def enqueue_message(self, queue_name: str, channel_id: str, thread_id: str, message_id: str, message_body: str, guid: Optional[str] = None) -> None:
        """
        Adds a message to the Azure Service Bus queue with a unique GUID for each message.
        """
        # Générer un GUID unique si non fourni
        guid = guid or str(uuid.uuid4())

        # Créer un ID de message complet pour garantir l'unicité
        full_message_id = f"{channel_id}_{thread_id}_{message_id}_{guid}"

        async with self.service_bus_client.get_queue_sender(queue_name) as sender:
            try:
                # Créer le message avec le corps et l'ID de message complet
                message = ServiceBusMessage(message_body)
                message.application_properties = {
                    'channel_id': channel_id,
                    'thread_id': thread_id,
                    'message_id': message_id,
                    'guid': guid,
                    'full_message_id': full_message_id
                }

                # Appliquer le TTL si défini pour la queue spécifique
                if queue_name == self.service_bus_config.SERVICE_BUS_MESSAGES_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_MESSAGES_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_INTERNAL_EVENTS_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_INTERNAL_EVENTS_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_EXTERNAL_EVENTS_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_EXTERNAL_EVENTS_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_WAIT_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_WAIT_QUEUE_TTL)

                # Envoyer le message dans la file d'attente
                await sender.send_messages(message)
                self.logger.info(f"Message enqueued with full_message_id: '{full_message_id}' to queue '{queue_name}'.")
            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to enqueue message to queue '{queue_name}': {str(e)}")


    async def dequeue_message(self, queue_name: str, channel_id: str, thread_id: str, message_id: str, guid: str) -> Optional[str]:
        """
        Removes a message from the Azure Service Bus queue based on channel_id, thread_id, message_id, and guid.
        """
        full_message_id = f"{channel_id}_{thread_id}_{message_id}_{guid}"

        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                received_messages = await receiver.receive_messages(max_message_count=1)
                if not received_messages:
                    self.logger.info(f"No messages found in queue '{queue_name}'.")
                    return None

                for message in received_messages:
                    # Vérifier si le message correspond à l'ID complet
                    if message.application_properties.get('full_message_id') == full_message_id:
                        self.logger.info(f"Message dequeued with full_message_id: '{full_message_id}' from queue '{queue_name}'.")
                        await receiver.complete_message(message)
                        return message.body.decode("utf-8")

                self.logger.info(f"Message '{full_message_id}' not found in queue '{queue_name}'.")
                return None
            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to dequeue message from queue '{queue_name}': {str(e)}")
                return None

    async def get_next_message(self, queue_name: str, channel_id: str, thread_id: str, current_message_id: str) -> Optional[str]:
        """
        Retrieves the next message in the queue for a given channel/thread after the current_message_id.
        """
        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                received_messages = await receiver.receive_messages(max_message_count=10)

                if not received_messages:
                    self.logger.info(f"No messages found in queue '{queue_name}'.")
                    return None

                current_timestamp = float(current_message_id)
                next_message = None

                for message in received_messages:
                    message_timestamp = float(message.application_properties.get('message_id', 0))
                    if message_timestamp > current_timestamp:
                        next_message = message
                        break

                if next_message:
                    self.logger.info(f"Next message found with message_id: '{next_message.application_properties['message_id']}' from queue '{queue_name}'.")
                    await receiver.complete_message(next_message)
                    return next_message.body.decode("utf-8")
                else:
                    self.logger.info(f"No next message found in queue '{queue_name}' after message_id '{current_message_id}'.")
                    return None

            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to retrieve next message from queue '{queue_name}': {str(e)}")
                return None


    async def get_all_messages(self, queue_name: str) -> List[str]:
        messages = []
        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                while True:
                    received_messages = await receiver.receive_messages(max_message_count=10)
                    if not received_messages:
                        break

                    for message in received_messages:
                        messages.append(message.body.decode("utf-8"))
                        await receiver.complete_message(message)

                self.logger.info(f"Retrieved {len(messages)} messages from queue '{queue_name}'.")
                return messages
            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to retrieve messages from queue '{queue_name}': {str(e)}")
                return []

    async def clear_messages_queue(self, queue_name: str) -> None:
        """
        Clears all messages in the Azure Service Bus queue.
        """
        self.logger.info(f"Clearing all messages in queue '{queue_name}'.")

        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                while True:
                    received_messages = await receiver.receive_messages(max_message_count=10)
                    if not received_messages:
                        break

                    for message in received_messages:
                        await receiver.complete_message(message)
                        self.logger.info(f"Message '{message.message_id}' successfully cleared from queue '{queue_name}'.")

            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to clear messages from queue '{queue_name}': {str(e)}")


    async def has_older_messages(self, queue_name: str, channel_id: str, thread_id: str, current_message_id: str) -> bool:
        """
        Checks if there are older messages in the queue, excluding the current message.
        """
        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                received_messages = await receiver.receive_messages(max_message_count=10)

                current_timestamp = float(current_message_id)
                older_messages = [msg for msg in received_messages if float(msg.application_properties.get('message_id', 0)) < current_timestamp]

                if older_messages:
                    self.logger.info(f"Found {len(older_messages)} older messages in queue '{queue_name}' excluding '{current_message_id}'.")
                    return True
                else:
                    self.logger.info(f"No older messages found in queue '{queue_name}' before '{current_message_id}'.")
                    return False

            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to check for older messages in queue '{queue_name}': {str(e)}")
                return False

    async def cleanup_expired_messages(self, queue_name: str, channel_id: str, thread_id: str, ttl_seconds: int) -> None:
        """
        Cleans up expired messages for a specific queue, channel, and thread based on TTL.
        """
        self.logger.info(f"Cleaning up expired messages in queue '{queue_name}' for channel '{channel_id}', thread '{thread_id}'.")

        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                received_messages = await receiver.receive_messages(max_message_count=10)

                for message in received_messages:
                    # Check if the message exceeds the TTL (manual enforcement)
                    if (datetime.utcnow() - message.enqueued_time_utc).total_seconds() > ttl_seconds:
                        self.logger.info(f"Message '{message.message_id}' exceeded TTL, removing it.")
                        await receiver.complete_message(message)

            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to clean expired messages from queue '{queue_name}': {str(e)}")
