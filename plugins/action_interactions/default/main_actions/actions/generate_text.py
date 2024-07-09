import json
import traceback

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class GenerateText(ActionBase):
    REQUIRED_PARAMETERS = ['text','model_name','context']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher : BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput , event: IncomingNotificationDataBase):

        try:
            parameters = action_input.parameters
            model_name = parameters.get('model_name', '')
            conversation = parameters.get('conversation', '')
            blob_name = f"{event.channel_id}-{event.thread_id}.txt"
            sessions = self.backend_internal_data_processing_dispatcher.sessions

            if conversation == True:
                conversation_data = await self.backend_internal_data_processing_dispatcher.read_data_content(sessions, blob_name) or "[]"
                if conversation_data is None:
                    self.logger.warning(f"The conversation {blob_name} returned is empty.")

                # Clean up conversation from system instruction
                conversation_json = json.loads(conversation_data)
                # Filter out elements with 'role: system'
                filtered_json = [item for item in conversation_json if item.get('role') != 'system']

                # Convert the filtered JSON back to a string
                filtered_string = json.dumps(filtered_json)
                conversation_data = filtered_string
                parameters['conversation_data'] = conversation_data  # Add conversation_data to parameters

            await self.user_interaction_dispatcher.send_message(f"Invoking model {model_name}...", event, message_type=MessageType.COMMENT)
            # Check if the model_name exists in the plugins
            if any(plugin.plugin_name == model_name for plugin in self.genai_interactions_text_dispatcher.plugins):
                # If the model_name exists, continue with the rest of the code
                result = await self.genai_interactions_text_dispatcher.handle_action(action_input, event, plugin_name=model_name)
                mind_message = f":speaking_head_in_silhouette: *UserInteraction [From {model_name}]:* {result}"
                await self.user_interaction_dispatcher.send_message(event=event, message=mind_message, message_type=MessageType.TEXT, is_internal=True)
                await self.user_interaction_dispatcher.send_message(result, event)
            else:
                # If the model_name does not exist, log an error message and return
                self.logger.error(f"The model {model_name} does not exist.")
                await self.user_interaction_dispatcher.send_message(f"Invalid GenAI model called [{model_name}] contact the bot owner if the problem persists.]", event, "comment")
                return


        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")


