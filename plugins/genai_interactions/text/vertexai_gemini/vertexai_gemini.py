import asyncio
import inspect
import json
import traceback
from typing import Any
import re
import vertexai
from google.oauth2 import service_account
from pydantic import BaseModel
from vertexai.preview.generative_models import GenerativeModel

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.message_type import MessageType
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)

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
        vertexai_gemini_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT["VERTEXAI_GEMINI"]
        self.vertexai_gemini_config = VertexaiGeminiConfig(**vertexai_gemini_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None

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

    def load_client(self):
        json_str = self.vertexai_gemini_key.replace("\n", "\\n")
        service_account_info = json.loads(json_str)
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        vertexai.init(project=self.vertexai_gemini_projectname, location=self.vertexai_gemini_location, credentials=credentials)
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
            parameters = action_input.parameters
            input_param: str = parameters.get('input', '')
            main_prompt = parameters.get('main_prompt', '')
            context = parameters.get('context', '')
            conversation_data = parameters.get('conversation_data', '')

            if main_prompt:
                self.logger.debug(f"Main prompt: {main_prompt}")
                init_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    data_container=self.backend_internal_data_processing_dispatcher.prompts, data_file=f"{main_prompt}.txt")
                if init_prompt is None:
                    self.logger.warning("No specific instructions")

                messages = [{"role": "system", "content": init_prompt}]
            else:
                messages = [{"role": "system", "content": "No specific instruction provided."}]

            if context:
                context_content = f"Here is additional context relevant to the following request: {context}"
                messages.append({"role": "user", "content": context_content})

            if conversation_data:
                conversation_content = f"Here is the conversation that led to the following request: {conversation_data}"
                messages.append({"role": "user", "content": conversation_content})

            user_content = input_param
            messages.append({"role": "user", "content": user_content})

            self.logger.info(f"GENERATE TEXT CALL: Calling Generative AI completion for user input on model {self.plugin_name}..")
            completion, genai_cost_base = await self.generate_completion(messages, event)

            # Update the costs
            costs = self.backend_internal_data_processing_dispatcher.costs
            original_msg_ts = event.thread_id if event.thread_id else event.timestamp
            blob_name = f"{event.channel_id}-{original_msg_ts}.txt"
            await self.input_handler.calculate_and_update_costs(genai_cost_base, costs, blob_name, event)

            # Update the session with the completion
            sessions = self.backend_internal_data_processing_dispatcher.sessions
            messages = json.loads(await self.backend_internal_data_processing_dispatcher.read_data_content(sessions, blob_name) or "[]")
            messages.append({"role": "assistant", "content": completion})
            completion_json = json.dumps(messages)
            await self.backend_internal_data_processing_dispatcher.write_data_content(sessions, blob_name, completion_json)
            return completion

        except ValueError as ve:
            self.logger.error(f"JSON parsing failed: {ve}")
            return "Error: The JSON text does not seem to be valid."
        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
            return None


    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase):

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
            response_text = first_candidate.content.parts[0].text

            # Calculate token usage details before any return statement
            usage_metadata = completion.usage_metadata
            self.genai_cost_base = GenAICostBase()
            self.genai_cost_base.total_tk = usage_metadata.total_token_count
            self.genai_cost_base.prompt_tk = usage_metadata.prompt_token_count
            self.genai_cost_base.completion_tk = usage_metadata.candidates_token_count
            self.genai_cost_base.input_token_price = self.vertexai_gemini_input_token_price
            self.genai_cost_base.output_token_price = self.vertexai_gemini_output_token_price

            # Process the response text to preserve newlines and Unicode characters
            formatted_response = self.process_response_text(response_text)

            # Return both the formatted response and genai_cost_base
            return formatted_response, self.genai_cost_base

        except asyncio.exceptions.CancelledError:
            # Handle task cancellation
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled", message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            raise

        except Exception as e:
            # Handle other exceptions that may occur
            self.logger.error(f"An error occurred: {str(e)}")
            raise

    def process_response_text(self, response_text):
        """Function to clean and format the response text by preserving newlines and Unicode characters."""
        if response_text:
            try:
                # Step 1: Remove the tags [BEGINIMDETECT], [ENDIMDETECT], ```json and ```.
                cleaned_text = re.sub(r'\[BEGINIMDETECT\]|\[ENDIMDETECT\]|```json|```', '', response_text).strip()

                # Step 2: Replace the \n characters in the JSON structure, but keep those inside string values.
                # To do this, we need to isolate valid JSON parts and process them separately.
                try:
                    # Extract the JSON block from the cleaned text
                    json_text = re.search(r'{.*}', cleaned_text, re.DOTALL).group(0)

                    # Remove newlines inside the JSON except for those inside strings
                    json_text_no_newlines = re.sub(r'(?<!\\)"[^"]*"(?!")|\n', lambda m: m.group(0).replace('\n', '') if m.group(0).startswith('"') else '', json_text)
                    formatted_response = f'[BEGINIMDETECT]{json_text_no_newlines}[ENDIMDETECT]'
                    return formatted_response
                except (json.JSONDecodeError, AttributeError):
                    self.logger.error(f"Invalid JSON response: {e}")
                    return "Error: The JSON text does not seem to be valid."

            except json.JSONDecodeError as e:
                # If JSON parsing fails, return the raw response text
                raise ValueError(f"JSON parsing failed: {e}")
        return response_text

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
