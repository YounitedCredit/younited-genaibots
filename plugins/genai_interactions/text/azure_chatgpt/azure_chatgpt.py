import asyncio
import inspect
import json
import traceback
from typing import Any

from openai import AsyncAzureOpenAI
from pydantic import BaseModel

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


class AzureChatGptConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_CHATGPT_INPUT_TOKEN_PRICE: float
    AZURE_CHATGPT_OUTPUT_TOKEN_PRICE: float
    AZURE_OPENAI_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    OPENAI_API_VERSION: str
    AZURE_CHATGPT_MODEL_NAME: str
    AZURE_CHATGPT_VISION_MODEL_NAME: str
    AZURE_CHATGPT_IS_ASSISTANT: bool = False  
    AZURE_CHATGPT_ASSISTANT_ID: str = None 


class AzureChatgptPlugin(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.config_manager : ConfigManager = global_manager.config_manager
        azure_chatgpt_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT["AZURE_CHATGPT"]
        self.azure_chatgpt_config = AzureChatGptConfig(**azure_chatgpt_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None

        # Dispatchers
        self.user_interaction_dispatcher = None
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None

    @property
    def plugin_name(self):
        return "azure_chatgpt"

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
        self.azure_openai_key = self.azure_chatgpt_config.AZURE_OPENAI_KEY
        self.azure_openai_endpoint = self.azure_chatgpt_config.AZURE_OPENAI_ENDPOINT
        self.openai_api_version = self.azure_chatgpt_config.OPENAI_API_VERSION
        self.model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME
        self.input_token_price = self.azure_chatgpt_config.AZURE_CHATGPT_INPUT_TOKEN_PRICE
        self.output_token_price = self.azure_chatgpt_config.AZURE_CHATGPT_OUTPUT_TOKEN_PRICE
        self.is_assistant = self.azure_chatgpt_config.AZURE_CHATGPT_IS_ASSISTANT
        self.assistant_id = self.azure_chatgpt_config.AZURE_CHATGPT_ASSISTANT_ID

        self.load_client()
        self.input_handler = ChatInputHandler(self.global_manager, self)
        self.input_handler.initialize()

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def load_client(self):
        try:
            self.gpt_client = AsyncAzureOpenAI(
                api_key=self.azure_chatgpt_config.AZURE_OPENAI_KEY,
                azure_endpoint=self.azure_chatgpt_config.AZURE_OPENAI_ENDPOINT,
                api_version=self.azure_chatgpt_config.OPENAI_API_VERSION
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
        # todo: add validation logic
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

    async def handle_action(self, action_input:ActionInput, event:IncomingNotificationDataBase):
        try:
            parameters = action_input.parameters
            input_param: str = parameters.get('input', '')
            main_prompt = parameters.get('main_prompt', '')
            context = parameters.get('context', '')
            conversation_data = parameters.get('conversation_data', '')

            if main_prompt:
                self.logger.debug(f"Main prompt: {main_prompt}")
                init_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=self.backend_internal_data_processing_dispatcher.prompts, data_file=f"{main_prompt}.txt")
                if init_prompt is None:
                    self.logger.warning("No specific instructions")

                messages = [{"role": "system", "content": init_prompt}]
            else:
                messages = [{"role": "system", "content": "No specific instruction provided."}]

            if context:
                context_content = f"Here is aditionnal context relevant to the following request: {context}"
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

        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")

    async def generate_completion_assistant(self, messages, event_data: IncomingNotificationDataBase):
        try:
            # Create a copy of the messages to avoid modifying the original list
            messages_copy = messages[:]

            # Initialize instructions as None
            instructions = None

            # Check for a system message in the copied list and handle it
            for i, message in enumerate(messages_copy):
                if message['role'] == "system":
                    instructions = message['content']
                    # Remove the system message from the copy, not the original
                    messages_copy.pop(i)
                    break

            # Create the thread
            thread = await self.gpt_client.beta.threads.create()

            # Add remaining messages to the thread
            for message in messages_copy:
                await self.gpt_client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role=message['role'],
                    content=message['content']
                )

            # Execute the assistant with instructions
            run = await self.gpt_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
                instructions=instructions  # Pass instructions separately
            )

            # Poll for completion
            while run.status in ['queued', 'in_progress', 'cancelling']:
                await asyncio.sleep(1)
                run = await self.gpt_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            if run.status == 'completed':
                response_messages = await self.gpt_client.beta.threads.messages.list(thread_id=thread.id)
                response = response_messages.data[0].content[0].text.value

                 # Extract the GPT response and token usage details
                self.genai_cost_base = GenAICostBase()
                total_tokens = sum([len(message.content[0].text.value) for message in response_messages.data])
                self.genai_cost_base.total_tk = total_tokens
                self.genai_cost_base.prompt_tk = total_tokens
                self.genai_cost_base.completion_tk = total_tokens
                self.genai_cost_base.input_token_price = self.input_token_price
                self.genai_cost_base.output_token_price = self.output_token_price
                return response, self.genai_cost_base
            elif run.status == 'requires_action':
                pass
            else:
                self.logger.error(f"Run status: {run.status}")
                return None, self.genai_cost_base

        except Exception as e:
            self.logger.error(f"An error occurred during assistant completion: {str(e)}")
            await self.user_interaction_dispatcher.send_message(
                event=event_data, 
                message="An unexpected error occurred during assistant completion", 
                message_type=MessageType.ERROR, 
                is_internal=True
            )
            raise


        
    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase):
        # Check if we should use the assistant
        self.logger.info("generate completion called")
        if self.azure_chatgpt_config.AZURE_CHATGPT_IS_ASSISTANT:
            return await self.generate_completion_assistant(messages, event_data)

        # If not using an assistant, proceed with the standard completion
        model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME

        if event_data.images:
            if not self.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME:
                self.logger.error("Image received without AZURE_CHATGPT_VISION_MODEL_NAME in config")
                await self.user_interaction_dispatcher.send_message(event=event_data, message="Image received without genai interpreter in config", message_type=MessageType.COMMENT)
                return
            model_name = self.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME
        else:
            model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME
            messages = await self.input_handler.filter_messages(messages)

        try:
            completion = await self.gpt_client.chat.completions.create(
                model=model_name,
                temperature=0.1,
                top_p=0.1,
                messages=messages,
                max_tokens=4096,
                seed=69
            )

            response = completion.choices[0].message.content
            # Extract the GPT response and token usage details
            self.genai_cost_base = GenAICostBase()
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

            AUTOMATED_RESPONSE_TRIGGER = "Automated response"
            event_copy = event

            if event.thread_id == '':
                response_id = event_copy.timestamp
            else:
                response_id = event_copy.thread_id

            event_copy.user_id = AUTOMATED_RESPONSE_TRIGGER
            event_copy.user_name =  AUTOMATED_RESPONSE_TRIGGER
            event_copy.user_email = AUTOMATED_RESPONSE_TRIGGER
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


class AzureChatgptInputHandler(BaseModel):
    pass
