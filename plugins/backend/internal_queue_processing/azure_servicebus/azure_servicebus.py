import logging
import time
import traceback
from typing import List, Optional, Tuple

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
from azure.core.exceptions import ServiceRequestError, ServiceResponseError
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


class AzureServiceBusQueuePlugin(InternalQueueProcessingBase):
    def __init__(self, global_manager: GlobalManager):
        self.logger = global_manager.logger

        super().__init__(global_manager)
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

    @property
    def messages_queue(self):
        return self.service_bus_config.SERVICE_BUS_MESSAGES_QUEUE
    
    @property
    def internal_events_queue(self):
        return self.service_bus_config.SERVICE_BUS_INTERNAL_EVENTS_QUEUE
    
    @property
    def external_events_queue(self):
        return self.service_bus_config.SERVICE_BUS_EXTERNAL_EVENTS_QUEUE
    
    @property
    def wait_queue(self):
        return self.service_bus_config.SERVICE_BUS_WAIT_QUEUE

    async def enqueue_message(self, queue_name: str, message: str) -> None:
        async with self.service_bus_client.get_queue_sender(queue_name) as sender:
            try:
                service_bus_message = ServiceBusMessage(message)
                await sender.send_messages(service_bus_message)
                self.logger.info(f"Message successfully enqueued to queue '{queue_name}'.")
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

    async def has_older_messages(self, queue_name: str) -> bool:
        messages = await self.get_all_messages(queue_name)
        if len(messages) > 0:
            return True
        return False
