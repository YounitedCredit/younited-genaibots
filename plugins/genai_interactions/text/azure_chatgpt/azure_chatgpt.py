import asyncio
import copy
import inspect
import json
import traceback
from datetime import datetime
from typing import Any
import uuid
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.backend.session_manager_dispatcher import SessionManagerDispatcher
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler
from utils.config_manager.config_manager import ConfigManager
from utils.plugin_manager.plugin_manager import PluginManager


class AzureChatGptConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_CHATGPT_INPUT_TOKEN_PRICE: float
    AZURE_CHATGPT_OUTPUT_TOKEN_PRICE: float
    AZURE_CHATGPT_OPENAI_KEY: str
    AZURE_CHATGPT_OPENAI_ENDPOINT: str
    AZURE_CHATGPT_OPENAI_API_VERSION: str
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
        self.azure_openai_key = self.azure_chatgpt_config.AZURE_CHATGPT_OPENAI_KEY
        self.azure_openai_endpoint = self.azure_chatgpt_config.AZURE_CHATGPT_OPENAI_ENDPOINT
        self.openai_api_version = self.azure_chatgpt_config.AZURE_CHATGPT_OPENAI_API_VERSION
        self.model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME
        self.plugin_name = self.azure_chatgpt_config.PLUGIN_NAME
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
        self.session_manager_dispatcher = self.global_manager.session_manager_dispatcher

    def load_client(self):
        try:
            self.gpt_client = AsyncAzureOpenAI(
                api_key=self.azure_openai_key,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.openai_api_version
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

    async def handle_request(self, event: IncomingNotificationDataBase):
        """Handles the request."""
        try:
            validate_request = self.validate_request(event)

            if not validate_request:
                self.logger.error(f"Invalid request: {event}")
                await self.dispatcher.send_message(
                    event.user_id,
                    "Something went wrong. Please try again or contact the bot owner.",
                    message_type=MessageType.COMMENT
                )
                return None

            response = await self.input_handler.handle_event_data(event)
            return response

        except Exception as e:
            error_trace = traceback.format_exc()
            self.logger.error(f"An error occurred: {e}\n{error_trace}")

            # Send message to the user
            await self.user_interaction_dispatcher.send_message(
                event.user_id,
                "Something went wrong. Please try again or contact the bot owner.",
                message_type=MessageType.COMMENT
            )

            # Send internal message with error details
            await self.user_interaction_dispatcher.send_message(
                "genai interaction issue",  # Replace with actual internal channel ID
                f"An error occurred in the azure_chatgpt module: {e}\n{error_trace}",
                message_type=MessageType.TEXT, is_internal=True
            )
            return None

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            # Extract parameters from the action input
            parameters = action_input.parameters
            input_param: str = parameters.get('input', '')
            messages = parameters.get('messages', [])
            main_prompt = parameters.get('main_prompt', '')
            context = parameters.get('context', '')
            model_name = parameters.get('model_name', '')
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

            # Append context and conversation data
            if context:
                target_messages.append({"role": "user", "content": f"Here is additional context: {context}"})
            if conversation_data:
                target_messages.append({"role": "user", "content": f"Conversation data: {conversation_data}"})

            # Append the user input
            target_messages.append({"role": "user", "content": input_param})

            # Call the model to generate the completion
            self.logger.info(f"GENAI CALL: Calling Generative AI completion for user input on model {model_name}..")
            generation_start_time = datetime.now()
            completion, genai_cost_base = await self.generate_completion(target_messages, event, raw_output=True)
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
                "model_name": self.model_name,
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
                    self.logger.info("Added image interpretations to the last user message")

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

    async def filter_messages(self, messages):
        filtered_messages = []
        for message in messages:
            # Si le message provient de l'utilisateur et que son contenu est une liste, nous filtrons le contenu 'image_url'
            if message['role'] == 'user' and isinstance(message['content'], list):
                filtered_content = [content for content in message['content'] if content['type'] != 'image_url']
                message['content'] = filtered_content
            filtered_messages.append(message)
        return filtered_messages

    async def filter_images(self, messages):
        filtered_messages = []
        for message in messages:
            # If the message is from the user and its content is a list, we filter out 'image_url' content.
            # This is because the GenAI model currently only supports text inputs, not images.
            if message['role'] == 'user' and isinstance(message['content'], list):
                filtered_content = [content for content in message['content'] if content['type'] != 'image_url']
                message['content'] = filtered_content
            filtered_messages.append(message)
        return filtered_messages

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase, raw_output= False):
        # Check if we should use the assistant
        self.logger.info("Generate completion triggered...")
        if self.azure_chatgpt_config.AZURE_CHATGPT_IS_ASSISTANT:
            return await self.generate_completion_assistant(messages, event_data)

        # If not using an assistant, proceed with the standard completion
        model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME

        # Filter out messages content from the metadata

        messages =  [{'role': message.get('role'), 'content': message.get('content')} for message in messages]

        if event_data.images:
            if not self.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME:
                self.logger.error("Image received without AZURE_CHATGPT_VISION_MODEL_NAME in config")
                await self.user_interaction_dispatcher.send_message(event=event_data, message="Image received without genai interpreter in config", message_type=MessageType.COMMENT)
                return
            model_name = self.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME
        else:
            model_name = self.azure_chatgpt_config.AZURE_CHATGPT_MODEL_NAME
            messages = await self.filter_images(messages)

        try:
            completion = await self.gpt_client.chat.completions.create(
                model=model_name,
                temperature=0.1,
                top_p=0.1,
                messages=messages,
                max_tokens=4096,
                seed=69
            )

            # Extract the full response between the markers
            response = completion.choices[0].message.content
            if raw_output == False:
                start_marker = "[BEGINIMDETECT]"
                end_marker = "[ENDIMDETECT]"

                # Ensure that the markers exist in the response
                if start_marker in response and end_marker in response:
                    # Extract the JSON content between the markers
                    json_content = response.split(start_marker)[1].split(end_marker)[0].strip()

                    # Load the JSON content
                    try:
                        response_dict = json.loads(json_content)
                        normalized_response_dict = self.normalize_keys(response_dict)

                        # Locate the "UserInteraction" action and replace escape sequences
                        for action in normalized_response_dict.get("response", []):
                            if action["Action"]["ActionName"] == "UserInteraction":
                                value = action["Action"]["Parameters"]["value"]

                                # Replace the escape sequences (\\n) with real newlines (\n)
                                formatted_value = value.replace("\\n", "\n")
                                action["Action"]["Parameters"]["value"] = formatted_value

                        # Rebuild the formatted JSON with indentation
                        formatted_json_content = json.dumps(response_dict, ensure_ascii=False, indent=2)
                        response = f"{start_marker}\n{formatted_json_content}\n{end_marker}"

                    except json.JSONDecodeError as e:
                        # Log error if JSON parsing fails
                        self.logger.error(f"Error decoding JSON: {e}")
                else:
                    self.logger.error("Missing [BEGINIMDETECT] or [ENDIMDETECT] markers in the response.")

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
            self.logger.error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")
            await self.user_interaction_dispatcher.send_message(event=event_data, message="An unexpected error occurred", message_type=MessageType.ERROR, is_internal=True)
            raise  # Re-raise the exception after logging


    async def trigger_genai(self, event :IncomingNotificationDataBase):

            AUTOMATED_RESPONSE_TRIGGER = "Automated response"
            event_copy = event

            if event.thread_id == '':
                response_id = event_copy.timestamp
            else:
                response_id = event_copy.thread_id

            event_copy.user_id = "AUTOMATED_RESPONSE"
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

    def camel_case(self, snake_str):
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)

    def normalize_keys(self, d):
        if isinstance(d, dict):
            return {self.camel_case(k): self.normalize_keys(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self.normalize_keys(i) for i in d]
        else:
            return d

    async def trigger_feedback(self, event: IncomingNotificationDataBase) -> Any:
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")
