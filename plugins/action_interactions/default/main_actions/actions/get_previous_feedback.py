import copy

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class GetPreviousFeedback(ActionBase):
    REQUIRED_PARAMETERS = ['value']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None
        self.internal_data_plugin = None
        self.feedbacks_container = None

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        NO_FEEDBACK_FOUND_MESSAGE = "No previous feedback found"
        event_copy = copy.deepcopy(event)
        event_copy.images = []
        event_copy.files_content = []
        self.feedbacks_container = self.backend_internal_data_processing_dispatcher.feedbacks
        category = action_input.parameters.get('Category', '')
        sub_category = action_input.parameters.get('SubCategory', '')

        # get global feedback
        blob_name = f"{category}_{sub_category}.txt"
        general_blob_name = f"{category}_Global.txt"
        feedbackprompt = ""
        existing_content = ""  # Initialize existing_content

        try:
            general_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=self.feedbacks_container, data_file=general_blob_name)
        except Exception as e:
            self.logger.error(f"Error reading general feedback: {str(e)}")
            general_content = ""

        try:
            existing_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=self.feedbacks_container, data_file=blob_name)
            if general_content:
                existing_content = general_content + "\n" + existing_content
        except Exception as e:
            self.logger.info(f"No previous feedback found for: {category}_{sub_category}. error: {e}")
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=":warningSorry there was an issue gathering previous feedback, ignoring this (but contact my administrator!)", message_type=MessageType.TEXT)
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=f"Error gathering previous feedback found for: {category}_{sub_category}. error: {e}", message_type=MessageType.COMMENT)

        if not existing_content:  # Changed condition
            event_copy.text = NO_FEEDBACK_FOUND_MESSAGE
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=NO_FEEDBACK_FOUND_MESSAGE, message_type=MessageType.COMMENT)
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=NO_FEEDBACK_FOUND_MESSAGE, message_type=MessageType.COMMENT,is_internal=True)
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
        else:
            feedbackprompt = f"Don't create another feedback from this as this is an automated message containing our insights from past interactions in the context of {category} {sub_category} :[{existing_content}]. Based on these informations follow next step of your current workflow."
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=f"Processing Previous feedback for [{blob_name}]...", message_type=MessageType.COMMENT)
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=f"Processing Previous feedback for [{blob_name}]: {existing_content}", message_type=MessageType.COMMENT, is_internal=True)
            event_copy.text = feedbackprompt
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)

    async def get_previous_feedback(self, category, sub_category):
        feedbackprompt = ""
        blob_name = f"{category}_{sub_category}.txt"
        general_blob_name = f"{category}_Global.txt"
        try:
            general_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=self.backend_internal_data_processing_dispatcher.feedbacks, data_file=general_blob_name)
        except Exception as e:
            self.logger.error(f"Error reading general feedback: {str(e)}")
            general_content = ""

        try:
            existing_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=self.backend_internal_data_processing_dispatcher.feedbacks, data_file=blob_name)
            if general_content:
                existing_content = general_content + "\n" + existing_content
        except Exception as e:
            self.logger.info(f"No previous feedback found for: {category}_{sub_category}. error: {e}")
            return None

        if existing_content == "" or existing_content == None:
            return None
        else:
            feedbackprompt = f"Don't create another feedback from this as this is an automated message containing our insights from past interactions in the context of {category} {sub_category} :[{existing_content}]. Based on these informations follow next step of your current workflow."
            return feedbackprompt
