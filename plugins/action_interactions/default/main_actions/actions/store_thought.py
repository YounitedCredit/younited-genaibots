import asyncio

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class StoreThought(ActionBase):
    REQUIRED_PARAMETERS = ['result', 'step', 'laststep']

    def __init__(self, global_manager):
        self.global_manager = global_manager
        self.logger = self.global_manager.logger

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            result = action_input.parameters.get('result')
            step = action_input.parameters.get('step')
            laststep = action_input.parameters.get('laststep', False)

            if not result:
                raise ValueError("Missing 'result' parameter")
            if not step:
                raise ValueError("Missing 'step' parameter")

            # Generate unique ID based on channel_id, thread_id, timestamp, and step
            unique_id = f"{event.channel_id}-{event.thread_id}-{event.timestamp}-{step}.txt"

            # Use the dispatcher to dynamically get the chainofthoughts container
            data_container = self.global_manager.backend_internal_data_processing_dispatcher.chainofthoughts

            # Write the result to the backend using the dispatcher
            await self.global_manager.backend_internal_data_processing_dispatcher.write_data_content(
                data_container=data_container,
                data_file=unique_id,
                data=result
            )

            self.logger.info(f"Stored thought for step {step} with ID {unique_id} in {data_container}")

            # If this is the last step, retrieve each thought and send as individual UserInteractions
            if laststep:
                files = await self.global_manager.backend_internal_data_processing_dispatcher.list_container_files(
                    container_name=data_container
                )

                # Filter and sort files by step
                base_id = f"{event.channel_id}-{event.thread_id}-{event.timestamp}"
                step_files = [f for f in files if f.startswith(base_id)]
                step_files_sorted = sorted(step_files, key=lambda x: int(x.split('-')[-1].split('.')[0]))

                # Retrieve and send each stored thought as a separate UserInteraction
                for filename in step_files_sorted:
                    filename_with_extension = f"{filename}.txt"

                    stored_data = await self.global_manager.backend_internal_data_processing_dispatcher.read_data_content(
                        data_container=data_container,
                        data_file=filename_with_extension
                    )

                    step_number = filename.split('-')[-1].split('.')[0]

                    # Send the stored result of each step as a separate message
                    await self.global_manager.user_interactions_dispatcher.send_message(
                        event=event,
                        message=f"Step {step_number}: {stored_data}",
                        message_type=MessageType.TEXT,
                        title=f"Step {step_number} Result",
                        is_internal=False
                    )
                    await asyncio.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"Failed to store thought: {e}")
            return False
