import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any

import vertexai
from google.oauth2 import service_account
from pydantic import BaseModel
from vertexai.preview.generative_models import GenerativeModel

from core.action_interactions.action_input import ActionInput
from core.backend.session_manager_dispatcher import SessionManagerDispatcher
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler
from utils.config_manager.config_manager import ConfigManager
from utils.plugin_manager.plugin_manager import PluginManager


class VertexaiGeminiConfig(BaseModel):
    PLUGIN_NAME: str
    VERTEXAI_GEMINI_INPUT_TOKEN_PRICE: float = 0.07
    VERTEXAI_GEMINI_OUTPUT_TOKEN_PRICE: float = 0.21
    VERTEXAI_GEMINI_MODELNAME: str
    VERTEXAI_GEMINI_PROJECTNAME: str
    VERTEXAI_GEMINI_LOCATION: str
    VERTEXAI_GEMINI_KEY: str
    VERTEXAI_GEMINI_MAX_OUTPUT_TOKENS: int
    VERTEXAI_GEMINI_TEMPERATURE: float
    VERTEXAI_GEMINI_TOP_P: float


class VertexaiGeminiPlugin(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        self.config_manager: ConfigManager = global_manager.config_manager
        vertexai_gemini_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT[
            "VERTEXAI_GEMINI"]
        self.vertexai_gemini_config = VertexaiGeminiConfig(**vertexai_gemini_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None
        self.model_name = self.vertexai_gemini_config.VERTEXAI_GEMINI_MODELNAME
        # Dispatchers
        self.user_interaction_dispatcher = None
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None

    @property
    def plugin_name(self):
        return "vertexai_gemini"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    @property
    def genai_cost_base(self) -> GenAICostBase:
        if self._genai_cost_base is None:
            raise ValueError("GenAI cost base is not set")
        return self._genai_cost_base

    @genai_cost_base.setter
    def genai_cost_base(self, value: GenAICostBase):
        self._genai_cost_base = value

    def initialize(self):
        # Client settings
        self.vertexai_gemini_input_token_price = self.vertexai_gemini_config.VERTEXAI_GEMINI_INPUT_TOKEN_PRICE
        self.vertexai_gemini_output_token_price = self.vertexai_gemini_config.VERTEXAI_GEMINI_OUTPUT_TOKEN_PRICE
        self.vertexai_gemini_projectname = self.vertexai_gemini_config.VERTEXAI_GEMINI_PROJECTNAME
        self.vertexai_gemini_location = self.vertexai_gemini_config.VERTEXAI_GEMINI_LOCATION
        self.vertexai_gemini_modelname = self.vertexai_gemini_config.VERTEXAI_GEMINI_MODELNAME
        self.vertexai_gemini_key = self.vertexai_gemini_config.VERTEXAI_GEMINI_KEY
        self.vertexai_gemini_max_output_tokens = self.vertexai_gemini_config.VERTEXAI_GEMINI_MAX_OUTPUT_TOKENS
        self.vertexai_gemini_top_p = self.vertexai_gemini_config.VERTEXAI_GEMINI_TOP_P
        self.vertexai_gemini_temperature = self.vertexai_gemini_config.VERTEXAI_GEMINI_TEMPERATURE

        self.load_client()
        self.input_handler = ChatInputHandler(self.global_manager, self)
        self.input_handler.initialize()

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.session_manager_dispatcher: SessionManagerDispatcher = self.global_manager.session_manager_dispatcher

    def load_client(self):
        json_str = self.vertexai_gemini_key.replace("\n", "\\n")
        service_account_info = json.loads(json_str)
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        vertexai.init(project=self.vertexai_gemini_projectname, location=self.vertexai_gemini_location,
                      credentials=credentials)
        self.client = GenerativeModel(self.vertexai_gemini_modelname)

    def validate_request(self, event: IncomingNotificationDataBase):
        """Determines whether the plugin can handle the given request."""
        return True

    async def handle_request(self, event: IncomingNotificationDataBase):
        """Handles the request."""
        validate_request = self.validate_request(event)

        response = await self.input_handler.handle_event_data(event)
        if validate_request == False:
            self.logger.error(f"Invalid request: {event}")
            return None
        else:
            return response

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            # Extract parameters from the action input
            parameters = action_input.parameters
            input_param: str = parameters.get('input', '')
            messages = parameters.get('messages', [])
            main_prompt = parameters.get('main_prompt', 'No specific instruction provided.')
            context = parameters.get('context', '')
            conversation_data = parameters.get('conversation_data', '')
            target_messages = []

            # Retrieve or create a session for this thread
            session = await self.global_manager.session_manager_dispatcher.get_or_create_session(
                channel_id=event.channel_id,
                thread_id=event.thread_id or event.timestamp,  # Use timestamp if thread_id is None
                enriched=True
            )

            # Capture the action invocation time
            action_start_time = datetime.now()

            # Add the automated user message to the session (with is_automated=True)
            automated_user_event = {
                'role': 'user',
                'content': [
                    {
                        'type': 'text',
                        'text': input_param
                    }
                ],
                'is_automated': True,
                'timestamp': action_start_time.isoformat()
            }
            self.session_manager_dispatcher.append_messages(session.messages, automated_user_event, session.session_id)

            # Prepare the system message for the assistant
            if main_prompt:
                init_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    data_container=self.backend_internal_data_processing_dispatcher.prompts,
                    data_file=f"{main_prompt}.txt"
                )
                if init_prompt:
                    target_messages.insert(0, {"role": "system", "content": init_prompt})
                else:
                    target_messages.insert(0, {"role": "system", "content": "No specific instruction provided."})
            else:
                target_messages.insert(0, {"role": "system", "content": "No specific instruction provided."})

            # Append context and conversation data
            if context:
                target_messages.append({"role": "user", "content": f"Here is additional context: {context}"})
            if conversation_data:
                target_messages.append({"role": "user", "content": f"Conversation data: {conversation_data}"})

            # Append the user input
            target_messages.append({"role": "user", "content": input_param})

            # Call the model to generate the completion
            self.logger.info(
                f"GENAI CALL: Calling Generative AI completion for user input on model {self.plugin_name}..")
            generation_start_time = datetime.now()

            # Ensure raw_output is set to True
            completion, genai_cost_base = await self.generate_completion(messages, event, raw_output=True)

            generation_end_time = datetime.now()

            # Calculate the generation time
            generation_time_ms = (generation_end_time - generation_start_time).total_seconds() * 1000

            # Process the completion response and costs
            input_cost = (genai_cost_base.prompt_tk / 1000) * genai_cost_base.input_token_price
            output_cost = (genai_cost_base.completion_tk / 1000) * genai_cost_base.output_token_price
            total_cost = input_cost + output_cost

            # Add the assistant's response to the session
            assistant_message = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": completion
                    }
                ],
                "timestamp": generation_end_time.isoformat(),
                "cost": {
                    "total_tokens": genai_cost_base.total_tk,
                    "prompt_tokens": genai_cost_base.prompt_tk,
                    "completion_tokens": genai_cost_base.completion_tk,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "total_cost": total_cost
                },
                "plugin_name": self.plugin_name,
                "model_name": self.vertexai_gemini_modelname,
                "generation_time_ms": generation_time_ms,
                "from_action": True,  # Indicate that the message comes from an action
                "action_payload": messages,  # Include the messages that were sent to the model
                "assistant_message_guid": str(uuid.uuid4())
            }

            # Add the assistant message to the session
            self.session_manager_dispatcher.append_messages(session.messages, assistant_message, session.session_id)

            # Update the total generation time in the session
            if not hasattr(session, 'total_time_ms'):
                session.total_time_ms = 0.0
            session.total_time_ms += generation_time_ms

            # Save the updated session
            await self.global_manager.session_manager_dispatcher.save_session(session)

            return completion

        except Exception as e:
            self.logger.error(f"Error in handle_action: {e}")
            raise

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase, raw_output: bool = False):

        messages = await self.input_handler.filter_messages(messages)

        try:
            # Convert messages to JSON format for API consumption
            messages_json = json.dumps(messages)
            # Prepare parameters for the request, including generation controls
            generation_params = {
                "temperature": self.vertexai_gemini_temperature,
                "top_p": self.vertexai_gemini_top_p,
                "max_tokens": self.vertexai_gemini_max_output_tokens
            }

            # Prepare the request payload
            request_payload = {
                "messages": messages,
                "parameters": generation_params
            }

            messages_json = json.dumps(request_payload, ensure_ascii=False)

            # Send the JSON data to the AI model and await the completion
            completion = await self.client.generate_content_async(messages_json)

            # Get the first candidate's response text from the 'parts' field
            first_candidate = completion.candidates[0]
            response = first_candidate.content.parts[0].text

            if not raw_output:
                start_marker = "[BEGINIMDETECT]"
                end_marker = "[ENDIMDETECT]"

                # Assurez-vous que les marqueurs existent dans la réponse
                if start_marker in response and end_marker in response:
                    # Extraire le contenu JSON entre les marqueurs
                    json_content = response.split(start_marker)[1].split(end_marker)[0].strip()

                    try:
                        response_dict = json.loads(json_content)
                        normalized_response_dict = self.normalize_keys(response_dict)

                        # Localiser l'action "UserInteraction" et remplacer les séquences d'échappement
                        for action in normalized_response_dict.get("response", []):
                            if action["Action"]["ActionName"] == "UserInteraction":
                                value = action["Action"]["Parameters"]["value"]
                                formatted_value = value.replace("\\n", "\n")  # Remplacer les séquences d'échappement
                                action["Action"]["Parameters"]["value"] = formatted_value

                        # Reconstruire le JSON formaté
                        formatted_json_content = json.dumps(response_dict, ensure_ascii=False, indent=2)
                        response = f"{start_marker}\n{formatted_json_content}\n{end_marker}"

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error decoding JSON: {e}")
                else:
                    self.logger.error("Missing [BEGINIMDETECT] or [ENDIMDETECT] markers in the response.")

            # Calculate token usage details before any return statement
            usage_metadata = completion.usage_metadata
            self.genai_cost_base = GenAICostBase()
            self.genai_cost_base.total_tk = usage_metadata.total_token_count
            self.genai_cost_base.prompt_tk = usage_metadata.prompt_token_count
            self.genai_cost_base.completion_tk = usage_metadata.candidates_token_count
            self.genai_cost_base.input_token_price = self.vertexai_gemini_input_token_price
            self.genai_cost_base.output_token_price = self.vertexai_gemini_output_token_price

            # Process the response text to preserve newlines and Unicode characters
            formatted_response = self.process_response_text(response)

            # Return both the formatted response and genai_cost_base
            return formatted_response, self.genai_cost_base

        except asyncio.exceptions.CancelledError:
            # Handle task cancellation
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled",
                                                                message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            raise

        except Exception as e:
            # Handle other exceptions that may occur
            self.logger.error(f"An error occurred: {str(e)}")
            raise

    def process_response_text(self, response_text):
        """Function to clean and format the response text by preserving newlines and Unicode characters."""
        if not response_text:
            self.logger.error("Empty response received")
            return None

        try:
            # Step 1: Remove the tags [BEGINIMDETECT], [ENDIMDETECT], ```json and ```.
            cleaned_text = re.sub(r'\[BEGINIMDETECT\]|\[ENDIMDETECT\]|```json|```', '', response_text).strip()

            # Step 2: Try to find a JSON object in the cleaned text
            json_match = re.search(r'{.*}', cleaned_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                # Remove newlines inside the JSON except for those inside strings
                json_text_no_newlines = re.sub(r'(?<!\\)"[^"]*"(?!")|\n',
                                               lambda m: m.group(0).replace('\n', '') if m.group(0).startswith(
                                                   '"') else '',
                                               json_text)
                formatted_response = f'[BEGINIMDETECT]{json_text_no_newlines}[ENDIMDETECT]'
                return formatted_response
            else:
                self.logger.warning(f"No JSON object found in response: {cleaned_text}")
                return cleaned_text  # Return the cleaned text if no JSON is found

        except Exception as e:
            self.logger.error(f"Error processing response text: {str(e)}")
            return None

    async def trigger_genai(self, event: IncomingNotificationDataBase):
        """Triggers an automated response for Generative AI."""
        try:
            self.logger.debug("Automated response triggered for Generative AI.")
            await self.handle_request(event)
        except Exception as e:
            self.logger.error(f"Error in trigger_genai: {str(e)}")

    async def trigger_feedback(self, event: IncomingNotificationDataBase) -> Any:
        """Trigger feedback process (currently a placeholder)."""
        self.logger.info(f"Feedback triggered for event: {event}")
        return {"status": "Feedback triggered successfully"}
