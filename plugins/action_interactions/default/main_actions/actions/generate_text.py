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
    REQUIRED_PARAMETERS = ['model_name', 'input']

    def __init__(self, global_manager):
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher: BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def format_llm_session(self, session):
        # Initialize an empty list to store the formatted interactions
        formatted_interactions = []

        # Iterate over each message in session.messages
        for message in session.messages:
            role = message.get('role')
            content = message.get('content')

            # Skip 'system' role messages
            if role == 'system':
                continue

            # If content is a list (like in user messages), extract text fields
            if isinstance(content, list):
                content = " ".join([item.get('text', '') for item in content])

            # Add the interaction to the formatted list
            formatted_interactions.append(f"{role}: {content}")

        # Join all interactions into a single string, separated by " | "
        return " | ".join(formatted_interactions)

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            parameters = action_input.parameters
            model_name = parameters.get('model_name', '')
            input_query = parameters.get('input', '')
            main_prompt = parameters.get('main_prompt', '')
            conversation = parameters.get('conversation', False)
            context = parameters.get('context', '')
            messages = parameters.get('messages', [])

            if not model_name or not input_query:
                await self.user_interaction_dispatcher.send_message(
                    message="Error: Missing mandatory parameters 'model_name' or 'input'.",
                    event=event,
                    message_type=MessageType.COMMENT
                )
                return

            # Build the system message (initial prompt)
            messages = []
            if main_prompt:
                # Fetch main prompt from the prompt manager if provided
                init_prompt = await self.global_manager.prompt_manager.get_main_prompt(main_prompt_file=main_prompt)

                if init_prompt:
                    messages.append({"role": "system", "content": init_prompt})
                else:
                    messages.append({"role": "system", "content": "No specific instruction provided."})
            else:
                messages.append({"role": "system", "content": "No specific instruction provided."})

            # Handle conversation history if requested
            if conversation:                
                session = await self.global_manager.session_manager.get_or_create_session(
                    channel_id=event.channel_id,
                    thread_id=event.thread_id or event.timestamp,  # Use timestamp if thread_id is None
                    enriched=True
                )
                
                if session:
                    # Concaténer le contenu de tous les messages de session.messages
                    concatenated_content = self.format_llm_session(session)
                    
                    # Ajouter le message concaténé à la liste des messages
                    messages.append({"role": "user", "content": concatenated_content})

            # Add context to the user input if provided
            if context:
                input_query = f"with the following context: {context}\n\nhere's the user query: {input_query}"

            # Add the user input
            messages.append({"role": "user", "content": input_query})
            
            action_input.parameters['messages'] = messages
            # Notify the user that the model invocation is starting
            await self.user_interaction_dispatcher.send_message(f"Invoking model {model_name}...", event, message_type=MessageType.COMMENT)

            # Check if the model exists in the plugins
            if any(plugin.plugin_name == model_name for plugin in self.genai_interactions_text_dispatcher.plugins):
                # Model found, handle the action with the model
                result = await self.genai_interactions_text_dispatcher.handle_action(action_input, event, plugin_name=model_name)

                # Send the result as an internal message and back to the user
                mind_message = f":speaking_head_in_silhouette: *UserInteraction [From {model_name}]:* {result}"
                await self.user_interaction_dispatcher.send_message(event=event, message=mind_message, message_type=MessageType.TEXT, is_internal=True)
                await self.user_interaction_dispatcher.send_message(result, event, action_ref="generate_text")
            else:
                # Model not found, log an error and send a message to the user
                self.logger.error(f"The model {model_name} does not exist.")
                await self.user_interaction_dispatcher.send_message(
                    message=f"Invalid GenAI model called [{model_name}]. Contact the bot owner if the problem persists.",
                    event=event,
                    message_type=MessageType.COMMENT,
                    action_ref="generate_text"
                )
                return

        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
            await self.user_interaction_dispatcher.send_message(
                message=f"An error occurred while processing your request: {e}",
                event=event,
                message_type=MessageType.COMMENT
            )
