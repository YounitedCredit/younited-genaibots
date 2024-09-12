
from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
import copy

class GetWholeConversation(ActionBase):
    REQUIRED_PARAMETERS = ['channel_id', 'thread_id']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput , event: IncomingNotificationDataBase ):
        # Extract the parameters
        parameters = action_input.parameters
        channel_id = parameters.get('channel_id')
        thread_id = parameters.get('thread_id')

        if not channel_id or not thread_id:
            return {"status": "error", "message": "Missing required parameters: channel_id or thread_id"}

        try:
            # Fetch conversation history using the method in SlackPlugin
            conversation_history = await self.user_interactions_dispatcher.fetch_conversation_history(
                event=event, channel_id=channel_id, thread_id=thread_id
            )

            if not conversation_history:
                return {"status": "error", "message": "No conversation history found."}

            # Build the formatted conversation string
            conversation_str = await self.build_conversation_string(conversation_history)

            # Send the conversation as a message
            llm_string = "Here's the  conversation history of the thread provided by the user, use this to answer its previous input:\n" + conversation_str
            event_copy = copy.deepcopy(event)
            event_copy.text = llm_string

            await self.genai_interactions_text_dispatcher.trigger_genai(event_copy)

        except Exception as e:
            self.global_manager.logger.error(f"Error in GetWholeConversation action: {e}")
            return {"status": "error", "message": str(e)}

    async def build_conversation_string(self, conversation_history):
        """
        Builds a formatted string based on the conversation history.
        """
        conversation_str = ""
        for message_event in conversation_history:
            # Format each message similarly to handle_thread_message_event
            conversation_str += (
                f"Timestamp: {message_event.converted_timestamp}, "
                f"Slack username: {message_event.user_name}, "
                f"Slack user id: {message_event.user_id}, "
                f"Slack user email: {message_event.user_email}, "
                f"Message: {message_event.text}\n"
            )
            # Optionally include file content or images if available
            if message_event.files_content:
                for file_content in message_event.files_content:
                    conversation_str += f"File content: {file_content}\n"
            if message_event.images:
                for base64_image in message_event.images:
                    conversation_str += f"Image (Base64 encoded): {base64_image[:50]}...\n"  # Only show part of the image content
        return conversation_str