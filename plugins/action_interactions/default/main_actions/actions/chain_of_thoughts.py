from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import IncomingNotificationDataBase
from core.user_interactions.message_type import MessageType
from core.genai_interactions.genai_interactions_text_dispatcher import GenaiInteractionsTextDispatcher
import copy

class ChainOfThoughts(ActionBase):
    REQUIRED_PARAMETERS = ['task', 'plan']

    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.logger = self.global_manager.logger
        self.accumulated_responses = []  # To accumulate all step responses

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            # Deep copy of the event and action input for processing
            self.event: IncomingNotificationDataBase = copy.deepcopy(event)
            self.action_input: ActionInput = action_input

            # Extract task and plan parameters
            task = action_input.parameters.get('task')
            plan = action_input.parameters.get('plan')

            # Validate if task and plan exist
            if not task or not plan:
                raise ValueError("Missing 'task' or 'plan' in parameters")

            # Send the task summary to the user or log it
            await self.user_interactions_dispatcher.send_message(
                event=event,
                message=f"Executing the task: {task}",
                message_type=MessageType.TEXT,
                title="Task Execution",
                is_internal=False
            )

            # Iterate over the steps in the plan
            for idx, step in enumerate(plan):
                step_message = f"Executing Step {idx + 1}: {step}"

                # Update the event with the step as the new prompt
                self.event.text = step
                self.event.files_content = []
                self.event.images = []

                # Trigger GenAI for this step using genai_interactions_text_dispatcher to generate a detailed response
                await self.genai_interactions_text_dispatcher.trigger_genai(event=self.event)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            await self.user_interactions_dispatcher.send_message(
                event=event,
                message=f"Error executing ChainOfThoughts: {str(e)}",
                message_type=MessageType.TEXT,
                title="Error",
                is_internal=True
            )
