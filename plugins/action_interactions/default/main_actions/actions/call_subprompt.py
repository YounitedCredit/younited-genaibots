import copy

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.get_previous_feedback import (
    GetPreviousFeedback,
)
from utils.prompt_manager.prompt_manager import PromptManager


class CallSubprompt(ActionBase):
    REQUIRED_PARAMETERS = ['value']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput , event: IncomingNotificationDataBase):
        self.prompt_manager : PromptManager = self.global_manager.prompt_manager
        event_copy = copy.deepcopy(event)
        event_copy.images = []
        event_copy.files_content = []
        feedbacks = None

        try:
            parameters = action_input.parameters
            message_type: str = parameters.get('value', '')
            category = parameters.get('feedback_category', '')
            sub_category = parameters.get('feedback_subcategory', '')

            if not message_type:
                self.logger.error("Error: 'Value' of Callsuprompt action is empty or None")
                await self.user_interactions_dispatcher.send_message(event=event, message="I didn't find the specific instruction sorry about that :-/, this is certainly an issue with my instructions, contact my administrator.", message_type=MessageType.TEXT, is_internal=False)
                return None
            else:
                await self.user_interactions_dispatcher.send_message(event=event, message=f"Invoking subprompt: [{message_type}]...", message_type=MessageType.COMMENT, is_internal=True)

            subprompt = await self.global_manager.prompt_manager.get_sub_prompt(message_type.lower())

            # get feedback if enabled
            if category and sub_category:
                self.logger.info(f"Feedback is enabled for this subprompt: {message_type} with category: {category} and subcategory: {sub_category}")
                feedback_action = GetPreviousFeedback(self.global_manager)
                feedbacks = await feedback_action.get_previous_feedback(category=category, sub_category=sub_category)
                if feedbacks:
                    subprompt = f"{subprompt}\n{feedbacks}"

            # save prompt
            if subprompt is not None:
                if feedbacks:
                    await self.user_interactions_dispatcher.send_message(event=event, message=f"Trigger subprompt [{message_type}] with feedback [{category}-{sub_category}]", message_type=MessageType.COMMENT, is_internal=False)
                    self.logger.info(f"launching completion on updated system prompt {message_type}")
                    event_copy.text = f"Here's updated instruction that you must consider as system instruction: {subprompt}. take also into account the previous feedback on this: {feedbacks}."
                else:
                    await self.user_interactions_dispatcher.send_message(event=event, message=f"Trigger subprompt [{message_type}]", message_type=MessageType.COMMENT, is_internal=False)
                    self.logger.info(f"launching completion on updated system prompt {message_type}")
                    event_copy.text = f"Here's updated instruction that you must consider as system instruction: {subprompt}."


                await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
            else:
                self.logger.warning(f"subprompt [{message_type}] not found")
                event_copy.text = "No subprompt found, explain to the user the situation, if you can try to help him rephrase its request, or to contact your administrator."
                await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)

        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")


