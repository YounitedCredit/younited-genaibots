from datetime import datetime, timedelta
from typing import List, Optional

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

    async def enqueue_message(self, queue_name: str, message_body: str) -> None:
        async with self.service_bus_client.get_queue_sender(queue_name) as sender:
            try:
                message = ServiceBusMessage(message_body)

                # Apply TTL based on the queue
                if queue_name == self.service_bus_config.SERVICE_BUS_MESSAGES_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_MESSAGES_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_INTERNAL_EVENTS_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_INTERNAL_EVENTS_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_EXTERNAL_EVENTS_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_EXTERNAL_EVENTS_QUEUE_TTL)
                elif queue_name == self.service_bus_config.SERVICE_BUS_WAIT_QUEUE:
                    self.apply_message_ttl(message, self.service_bus_config.SERVICE_BUS_WAIT_QUEUE_TTL)

                await sender.send_messages(message)
                self.logger.info(f"Message successfully enqueued to queue '{queue_name}' with TTL.")
            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to enqueue message to queue '{queue_name}': {str(e)}")

    async def dequeue_message(self, queue_name: str) -> Optional[str]:
        async with self.service_bus_client.get_queue_receiver(queue_name, max_wait_time=5) as receiver:
            try:
                received_messages = await receiver.receive_messages(max_message_count=1)
                if not received_messages:
                    self.logger.info(f"No messages found in queue '{queue_name}'.")
                    return None

                for message in received_messages:
                    # Check if the message exceeds the TTL (manual enforcement)
                    if message.time_to_live and (datetime.now() - message.enqueued_time_utc).seconds > message.time_to_live.seconds:
                        self.logger.info(f"Message '{message.message_id}' exceeded TTL, moving to dead-letter queue.")
                        await receiver.dead_letter_message(message)
                        continue

                    self.logger.info(f"Message dequeued from queue '{queue_name}': {message.body}")
                    await receiver.complete_message(message)
                    return message.body.decode("utf-8")
            except (ServiceRequestError, ServiceResponseError) as e:
                self.logger.error(f"Failed to dequeue message from queue '{queue_name}': {str(e)}")
                return None

    async def get_next_message(self, queue_name: str) -> Optional[str]:
        return await self.dequeue_message(queue_name)

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

    async def has_older_messages(self, queue_name: str, current_message_id: str) -> bool:
        """
        Checks if there are older messages in the queue, excluding the current message.
        """
        self.logger.info(f"Checking for older messages in queue '{queue_name}', excluding message_id '{current_message_id}'.")
        try:
            messages = await self.get_all_messages(queue_name)

            # Filter out the current message by comparing IDs
            filtered_messages = [msg for msg in messages if current_message_id not in msg]

            # Log filtered messages for debugging
            self.logger.debug(f"Filtered messages (excluding current): {filtered_messages}")

            return len(filtered_messages) > 0
        except (ServiceRequestError, ServiceResponseError) as e:
            self.logger.error(f"Failed to check for older messages in queue '{queue_name}': {str(e)}")
            return False
