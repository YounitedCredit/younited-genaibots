import asyncio
import inspect
import json
import traceback
from typing import Any
from datetime import datetime
from mistralai.client import MistralClient
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
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


class AzureMistralConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_MISTRAL_INPUT_TOKEN_PRICE: float
    AZURE_MISTRAL_OUTPUT_TOKEN_PRICE: float
    AZURE_MISTRAL_KEY: str
    AZURE_MISTRAL_ENDPOINT: str
    AZURE_MISTRAL_MODELNAME: str

class AzureMistralPlugin(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.config_manager : ConfigManager = global_manager.config_manager
        azure_mistral_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT["AZURE_MISTRAL"]
        self.azure_mistral_config = AzureMistralConfig(**azure_mistral_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None
        self.session_manager = self.global_manager.session_manager

        # Dispatchers
        self.user_interaction_dispatcher = None
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None

    @property
    def plugin_name(self):
        return "azure_mistral"

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
        self.azure_mistral_key = self.azure_mistral_config.AZURE_MISTRAL_KEY
        self.azure_mistral_endpoint = self.azure_mistral_config.AZURE_MISTRAL_ENDPOINT
        self.azure_mistral_modelname = self.azure_mistral_config.AZURE_MISTRAL_MODELNAME
        self.input_token_price = self.azure_mistral_config.AZURE_MISTRAL_INPUT_TOKEN_PRICE
        self.output_token_price = self.azure_mistral_config.AZURE_MISTRAL_OUTPUT_TOKEN_PRICE

        self.load_client()
        self.input_handler = ChatInputHandler(self.global_manager, self)
        self.input_handler.initialize()

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher : BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def load_client(self):
        try:
            self.mistral_client = MistralClient(
                endpoint=self.azure_mistral_endpoint, api_key=self.azure_mistral_key
            )
        except KeyError as e:
            self.logger.error(f"Missing configuration key: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Invalid configuration value: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while loading Azure OpenAI client: {e}")
            raise

    def validate_request(self, event:IncomingNotificationDataBase):
        """Determines whether the plugin can handle the given request."""
        # Check if the request is a valid request for this plugin
        return True

    async def handle_request(self, event:IncomingNotificationDataBase):
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
            main_prompt = parameters.get('main_prompt', '')
            context = parameters.get('context', '')
            conversation_data = parameters.get('conversation_data', '')

            # Always retrieve the session for this thread (since we're in a thread context)
            session = await self.session_manager.get_or_create_session(
                event.origin_plugin_name,
                event.channel_id,
                event.thread_id,
                "",  # core_prompt not needed since the session already exists
                "",  # main_prompt not needed since the session already exists
                datetime.now().isoformat(),
                enriched=True  # Ensure we're working with an enriched session
            )

            # Capture the action invocation time
            action_start_time = datetime.now()

            # Add action input details to the session
            action_event_data = {
                'action_name': action_input.action_name,
                'parameters': parameters,
                'input': input_param,
                'context': context,
                'conversation_data': conversation_data,
                'timestamp': action_start_time.isoformat()  # Add the timestamp when the action started
            }
            await self.session_manager.add_event_to_session(session, 'action_invocation', action_event_data)

            # Build the messages for the model call
            if main_prompt:
                self.logger.debug(f"Main prompt: {main_prompt}")
                init_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    data_container=self.backend_internal_data_processing_dispatcher.prompts,
                    data_file=f"{main_prompt}.txt"
                )
                if init_prompt is None:
                    self.logger.warning("No specific instructions found, using default.")
                    init_prompt = "No specific instruction provided."
            else:
                init_prompt = "No specific instruction provided."

            messages = [{"role": "system", "content": init_prompt}]

            # Append context and conversation data
            if context:
                context_content = f"Here is additional context relevant to the following request: {context}"
                messages.append({"role": "user", "content": context_content})

            if conversation_data:
                conversation_content = f"Here is the conversation that led to the following request:``` {conversation_data} ```"
                messages.append({"role": "user", "content": conversation_content})

            # Append the user input to the messages
            user_content = input_param
            messages.append({"role": "user", "content": user_content})

            # Call the model to generate the completion
            self.logger.info(f"GENERATE TEXT CALL: Calling Generative AI completion for user input on model {self.plugin_name}..")
            
            # Record the time before completion generation
            generation_start_time = datetime.now()

            # Generate the completion
            completion, genai_cost_base = await self.generate_completion(messages, event)

            # Calculate the generation time
            generation_end_time = datetime.now()
            generation_duration = (generation_end_time - generation_start_time).total_seconds()

            # Update the costs
            costs = self.backend_internal_data_processing_dispatcher.costs
            original_msg_ts = event.thread_id if event.thread_id else event.timestamp
            blob_name = f"{event.channel_id}-{original_msg_ts}.txt"
            await self.input_handler.calculate_and_update_costs(genai_cost_base, costs, blob_name, event)

            # Update the session with the model's completion and costs
            assistant_response_event = {
                'role': 'assistant',
                'content': completion,
                'generation_time': generation_duration,  # Add the generation time
                'cost': {
                    'total_tokens': genai_cost_base.total_tk,
                    'prompt_tokens': genai_cost_base.prompt_tk,
                    'completion_tokens': genai_cost_base.completion_tk,
                    'input_cost': genai_cost_base.input_token_price,
                    'output_cost': genai_cost_base.output_token_price
                }
            }
            await self.session_manager.add_event_to_session(session, 'assistant_completion', assistant_response_event)

            # Save the enriched session after the action and model invocation
            await self.session_manager.save_session(session)

            # Update the session with the completion (keeping the original Mistral implementation)
            sessions = self.backend_internal_data_processing_dispatcher.sessions
            messages = json.loads(await self.backend_internal_data_processing_dispatcher.read_data_content(sessions, blob_name) or "[]")
            messages.append({"role": "assistant", "content": completion})
            completion_json = json.dumps(messages)
            await self.backend_internal_data_processing_dispatcher.write_data_content(sessions, blob_name, completion_json)

            return completion

        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")
            raise

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase):

        messages = await self.input_handler.filter_messages(messages)

        try:
            completion = self.mistral_client.chat(
                model=self.azure_mistral_modelname,
                messages=messages,
                temperature=0.1,
                top_p=0.1,
            )

            response = completion.choices[0].message.content
            # Extract the GPT response and token usage details
            # Create an instance of GenAICostBase without arguments
            self.genai_cost_base = GenAICostBase()
            # Set the attributes
            self.genai_cost_base.total_tk = completion.usage.total_tokens
            self.genai_cost_base.prompt_tk = completion.usage.prompt_tokens
            self.genai_cost_base.completion_tk = completion.usage.completion_tokens
            self.genai_cost_base.input_token_price = self.input_token_price
            self.genai_cost_base.output_token_price = self.output_token_price

            return response, self.genai_cost_base

        except asyncio.exceptions.CancelledError:
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled", message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
            await self.user_interaction_dispatcher.send_message(event=event_data, message="An unexpected error occurred", message_type=MessageType.ERROR, is_internal=True)
            raise  # Re-raise the exception after logging

    async def trigger_genai(self, event :IncomingNotificationDataBase):
            event_copy = event

            if event.thread_id == '':
                response_id = event_copy.timestamp
            else:
                response_id = event_copy.thread_id

            AUTOMATED_RESPONSE = "AUTOMATED_RESPONSE"
            event_copy.user_id = "AUTOMATED_RESPONSE"
            event_copy.user_name =  AUTOMATED_RESPONSE
            event_copy.user_email = AUTOMATED_RESPONSE
            event_copy.event_label = "thread_message"
            user_message = self.user_interaction_dispatcher.format_trigger_genai_message(event=event, message=event_copy.text)
            event_copy.text = user_message
            event_copy.is_mention = True
            event_copy.thread_id = response_id

            self.logger.debug(f"Triggered automated response on behalf of the user: {event_copy.text}")
            await self.user_interaction_dispatcher.send_message(event=event_copy, message= "Processing incoming data, please wait...", message_type=MessageType.COMMENT)

            # Count the number of words in event_copy.text
            word_count = len(event_copy.text.split())

            # If there are more than 300 words, call plugin.file_upload
            if word_count > 300:
                await self.user_interaction_dispatcher.upload_file(event=event_copy, file_content=event_copy.text, filename="Bot reply.txt", title=":zap::robot_face: Automated User Input", is_internal=True)
            else:
                await self.user_interaction_dispatcher.send_message(event=event_copy, message= f":zap::robot_face: *AutomatedUserInput*: {event_copy.text}", message_type=MessageType.TEXT, is_internal= True)

            await self.global_manager.user_interactions_behavior_dispatcher.process_incoming_notification_data(event_copy)

    async def trigger_feedback(self, event: IncomingNotificationDataBase) -> Any:
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")
