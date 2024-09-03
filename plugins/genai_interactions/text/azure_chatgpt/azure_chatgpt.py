import asyncio
import inspect
import json
import traceback
from typing import Any
import copy
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
            self.logger.info("Starting generate_completion_assistant method")
            messages_copy = copy.deepcopy(messages)
            instructions = None
            user_query = None
            last_user_message_index = None

            # Extract instructions if present (should be the first message)
            if messages_copy and messages_copy[0]['role'] == 'system':
                instructions = messages_copy.pop(0)['content']
                self.logger.info("Extracted instructions from system message")

            # Find the last user message and extract query
            last_user_message = None
            for message in reversed(messages_copy):
                if message['role'] == 'user':
                    last_user_message = message
                    break

            if last_user_message:
                content = last_user_message['content']
                if isinstance(content, list) and len(content) > 0:
                    user_query = content[0]['text'] if content[0]['type'] == 'text' else ''
                else:
                    user_query = content

                last_user_message_index = messages_copy.index(last_user_message)
                self.logger.info(f"Extracted user query: {user_query[:50]}...")  # Log first 50 chars of query
            else:
                self.logger.warning("No user message found")
                user_query = ""
                last_user_message_index = None

            thread = await self.gpt_client.beta.threads.create()
            self.logger.info(f"Created new thread with ID: {thread.id}")

            # Handle images if present
            if event_data.images:
                self.logger.info(f"Processing {len(event_data.images)} images")
                vision_model = self.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME
                if not vision_model:
                    raise ValueError("Image received but AZURE_CHATGPT_VISION_MODEL_NAME not configured")
                
                self.logger.info(f"Using vision model: {vision_model}")
                image_interpretations = []
                for i, base64_image in enumerate(event_data.images):
                    self.logger.info(f"Interpreting image {i+1}/{len(event_data.images)}")
                    image_prompt = (
                        f"Please provide a detailed description of this image in the context of the following user query: '{user_query}'. "
                        "Include all relevant details, colors, text, objects, and their relationships. "
                        "If there are any aspects of the image that seem particularly relevant to the query, emphasize those. give as much detail as possible on what is provided in this, provide a long answer."
                    )

                    image_message = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }

                    self.logger.info("Calling vision model for image interpretation")
                    image_completion = await self.gpt_client.chat.completions.create(
                        model=vision_model,
                        messages=[
                            {"role": "user", "content": [
                                {"type": "text", "text": image_prompt},
                                image_message
                            ]}
                        ]
                    )
                    interpretation = image_completion.choices[0].message.content
                    self.logger.info(f"Image {i+1} interpretation: {interpretation[:50]}...")  # Log first 50 chars
                    image_interpretations.append(interpretation)
                
                # Ajout des interprétations d'images au dernier message utilisateur
                if last_user_message_index is not None:
                    automated_response = (
                        "\n\n[Automated Response] "
                        "Here are detailed descriptions of the images I've uploaded, relevant to my query: "
                        f"{'; '.join(image_interpretations)}"
                    )
                    if isinstance(messages_copy[last_user_message_index]['content'], list):
                        messages_copy[last_user_message_index]['content'] = [
                            item for item in messages_copy[last_user_message_index]['content']
                            if item['type'] == 'text'
                        ]
                        messages_copy[last_user_message_index]['content'].append({
                            'type': 'text',
                            'text': automated_response
                        })
                    else:
                        messages_copy[last_user_message_index]['content'] += automated_response
                    self.logger.info(f"Added image interpretations to the last user message")

            # Remove images from event_data to avoid sending them again
            event_data.images = []

            # Add messages to the thread
            self.logger.info(f"Adding {len(messages_copy)} messages to the thread")
            for message in messages_copy:
                content = message['content']
                if isinstance(content, list):
                    text_content = ' '.join([item['text'] for item in content if item['type'] == 'text'])
                else:
                    text_content = content

                await self.gpt_client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role=message['role'],
                    content=text_content
                )

            # Execute the assistant with instructions
            self.logger.info(f"Executing assistant with ID: {self.assistant_id}")
            run = await self.gpt_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
                instructions=instructions
            )

            # Poll for completion
            self.logger.info("Polling for run completion")
            while run.status in ['queued', 'in_progress', 'cancelling']:
                self.logger.info(f"Run status: {run.status}")
                await asyncio.sleep(1)
                run = await self.gpt_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            self.logger.info(f"Run completed with status: {run.status}")
            if run.status == 'completed':
                response_messages = await self.gpt_client.beta.threads.messages.list(thread_id=thread.id)
                response = response_messages.data[0].content[0].text.value
                self.logger.info(f"Received response: {response[:100]}...")  # Log first 100 chars of response

                # Extract the GPT response and token usage details
                self.genai_cost_base = GenAICostBase()
                total_tokens = sum([len(message.content[0].text.value) for message in response_messages.data])
                self.logger.info(f"Total tokens used: {total_tokens}")
                self.genai_cost_base.total_tk = total_tokens
                self.genai_cost_base.prompt_tk = total_tokens
                self.genai_cost_base.completion_tk = total_tokens
                self.genai_cost_base.input_token_price = self.input_token_price
                self.genai_cost_base.output_token_price = self.output_token_price
                return response, self.genai_cost_base
            elif run.status == 'requires_action':
                self.logger.warning("Run requires action, not implemented in this version")
                pass
            else:
                self.logger.error(f"Run failed with status: {run.status}")
                return None, self.genai_cost_base

        except Exception as e:
            self.logger.error(f"An error occurred during assistant completion: {str(e)}")
            self.logger.error(traceback.format_exc())  # Log the full stack trace
            await self.user_interaction_dispatcher.send_message(
                event=event_data, 
                message="An unexpected error occurred during assistant completion", 
                message_type=MessageType.COMMENT, 
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
