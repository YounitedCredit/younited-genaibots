# submit_feedback.py

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class SubmitFeedback(ActionBase):
    REQUIRED_PARAMETERS = ['Category', 'SubCategory', 'Summary']

    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.user_interactions_text_plugin = None
        self.internal_data_plugin = None
        self.logger = self.global_manager.logger
        self.feedbacks_container = None

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher: GenAIInteractionsTextPluginBase = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        self.feedbacks_container = self.backend_internal_data_processing_dispatcher.feedbacks
        category = action_input.parameters.get('Category', '')
        sub_category = action_input.parameters.get('SubCategory', '')
        feedback_summary = action_input.parameters.get('Summary', '')
        file_name = f"{category}_{sub_category}.txt"

        try:
            existing_content = await self.backend_internal_data_processing_dispatcher.read_data_content(
                data_container=self.feedbacks_container, data_file=file_name)
        except Exception:
            self.logger.info(f"No previous feedback found for: {category}_{sub_category}")
            existing_content = ""  # Utiliser une chaîne vide si le contenu existant n'est pas trouvé

        if existing_content is None:
            existing_content = ''

        new_content = "".join([existing_content, feedback_summary, "\n"])
        self.logger.info(f"Adding new feedback to existing content: {feedback_summary}")
        try:
            await self.backend_internal_data_processing_dispatcher.write_data_content(
                data_container=self.feedbacks_container, data_file=file_name, data=new_content)
            self.logger.info(f"Feedback stored in {file_name}")
        except Exception as e:
            self.logger.error(f"An error occurred while writing feedback: {e}")
