import asyncio
import json
import traceback
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
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
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler
from utils.config_manager.config_manager import ConfigManager
from utils.plugin_manager.plugin_manager import PluginManager


class OpenAIChatGptConfig(BaseModel):
    PLUGIN_NAME: str
    OPENAI_CHATGPT_API_KEY: str
    OPENAI_CHATGPT_MODEL_NAME: str
    OPENAI_CHATGPT_VISION_MODEL_NAME: str
    OPENAI_CHATGPT_INPUT_TOKEN_PRICE: float
    OPENAI_CHATGPT_OUTPUT_TOKEN_PRICE: float
    OPENAI_CHATGPT_IS_ASSISTANT: bool = False
    OPENAI_CHATGPT_ASSISTANT_ID: str = None


class OpenaiChatgptPlugin(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        self.config_manager: ConfigManager = global_manager.config_manager
        openai_chatgpt_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT["OPENAI_CHATGPT"]
        self.openai_chatgpt_config = OpenAIChatGptConfig(**openai_chatgpt_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None
        self.session_manager = self.global_manager.session_manager

        # Dispatchers
        self.user_interaction_dispatcher = None
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None

    @property
    def plugin_name(self):
        return "openai_chatgpt"

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
        self.openai_api_key = self.openai_chatgpt_config.OPENAI_CHATGPT_API_KEY
        self.model_name = self.openai_chatgpt_config.OPENAI_CHATGPT_MODEL_NAME
        self.input_token_price = self.openai_chatgpt_config.OPENAI_CHATGPT_INPUT_TOKEN_PRICE
        self.output_token_price = self.openai_chatgpt_config.OPENAI_CHATGPT_OUTPUT_TOKEN_PRICE
        self.is_assistant = self.openai_chatgpt_config.OPENAI_CHATGPT_IS_ASSISTANT
        self.assistant_id = self.openai_chatgpt_config.OPENAI_CHATGPT_ASSISTANT_ID

        # Set OpenAI API key
        AsyncOpenAI.api_key = self.openai_api_key
        self.input_handler = ChatInputHandler(self.global_manager, self)
        self.input_handler.initialize()

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def validate_request(self, event: IncomingNotificationDataBase):
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

            await self.user_interaction_dispatcher.send_message(
                event.user_id,
                "Something went wrong. Please try again or contact the bot owner.",
                message_type=MessageType.COMMENT
            )

            await self.user_interaction_dispatcher.send_message(
                "genai interaction issue",
                f"An error occurred in the openai_chatgpt module: {e}\n{error_trace}",
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

            # Retrieve or create a session for this thread
            session = await self.global_manager.session_manager.get_or_create_session(
                channel_id=event.channel_id,
                thread_id=event.thread_id or event.timestamp,  # Use timestamp if thread_id is None
                enriched=True
            )

            # Capture the action invocation time
            action_start_time = datetime.now()

            # Add the automated user message to the session (with is_automated=True)
            automated_user_event = {
                'role': 'user',
                'content': input_param,
                'is_automated': True,
                'timestamp': action_start_time.isoformat()
            }
            session.messages.append(automated_user_event)  # Append the automated message to the session

            # Prepare the system message for the assistant
            if main_prompt:
                init_prompt = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    data_container=self.backend_internal_data_processing_dispatcher.prompts,
                    data_file=f"{main_prompt}.txt"
                )
                if init_prompt:
                    messages.insert(0, {"role": "system", "content": init_prompt})
            else:
                messages.insert(0, {"role": "system", "content": "No specific instruction provided."})

            # Append context and conversation data
            if context:
                messages.append({"role": "user", "content": f"Here is additional context: {context}"})
            if conversation_data:
                messages.append({"role": "user", "content": f"Conversation data: {conversation_data}"})

            # Append the user input
            messages.append({"role": "user", "content": input_param})

            # Call the model to generate the completion
            self.logger.info(f"GENAI CALL: Calling Generative AI completion for user input on model {model_name}..")
            generation_start_time = datetime.now()
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
                "content": completion,  # Strip markers if needed
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
                "action_payload": messages  # Include the messages that were sent to the model
            }

            # Add the assistant message to the session
            session.messages.append(assistant_message)

            # Update the total generation time in the session
            if not hasattr(session, 'total_time_ms'):
                session.total_time_ms = 0.0
            session.total_time_ms += generation_time_ms

            # Save the updated session
            await self.global_manager.session_manager.save_session(session)

            return completion

        except Exception as e:
            self.logger.error(f"Error in handle_action: {e}")
            raise

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase, raw_output= False):
        # Check if we should use the assistant
        self.logger.info("Generate completion triggered...")

        # If not using an assistant, proceed with the standard completion
        model_name = self.openai_chatgpt_config.OPENAI_CHATGPT_MODEL_NAME

        # Filter out messages content from the metadata

        messages =  [{'role': message.get('role'), 'content': message.get('content')} for message in messages]

        if event_data.images:
            if not self.openai_chatgpt_config.OPENAI_CHATGPT_VISION_MODEL_NAME:
                self.logger.error("Image received without AZURE_CHATGPT_VISION_MODEL_NAME in config")
                await self.user_interaction_dispatcher.send_message(event=event_data, message="Image received without genai interpreter in config", message_type=MessageType.COMMENT)
                return
            model_name = self.openai_chatgpt_config.OPENAI_CHATGPT_VISION_MODEL_NAME
        else:
            model_name = self.openai_chatgpt_config.OPENAI_CHATGPT_MODEL_NAME
            messages = await self.filter_images(messages)

        try:
            client = AsyncOpenAI(api_key=self.openai_api_key)
            completion = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=4096
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

        except asyncio.CancelledError:
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled", message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            raise
        except asyncio.exceptions.CancelledError:
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled", message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")
            await self.user_interaction_dispatcher.send_message(event=event_data, message="An unexpected error occurred", message_type=MessageType.COMMENT, is_internal=True)
            raise  # Re-raise the exception after logging

    async def filter_images(self, messages):
        filtered_messages = []
        for message in messages:
            if message['role'] == 'user' and isinstance(message['content'], list):
                filtered_content = [content for content in message['content'] if content['type'] != 'image_url']
                message['content'] = filtered_content
            filtered_messages.append(message)
        return filtered_messages

    async def trigger_genai(self, event: IncomingNotificationDataBase):
        AUTOMATED_RESPONSE_TRIGGER = "Automated response"
        event_copy = event

        if event.thread_id == '':
            response_id = event_copy.timestamp
        else:
            response_id = event_copy.thread_id

        event_copy.user_id = "AUTOMATED_RESPONSE"
        event_copy.user_name = AUTOMATED_RESPONSE_TRIGGER
        event_copy.user_email = AUTOMATED_RESPONSE_TRIGGER
        event_copy.event_label = "thread_message"
        user_message = self.user_interaction_dispatcher.format_trigger_genai_message(event=event, message=event_copy.text)
        event_copy.text = user_message
        event_copy.is_mention = True
        event_copy.thread_id = response_id

        self.logger.debug(f"Triggered automated response on behalf of the user: {event_copy.text}")
        await self.user_interaction_dispatcher.send_message(event=event_copy, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)

        word_count = len(event_copy.text.split())

        if word_count > 300:
            await self.user_interaction_dispatcher.upload_file(event=event_copy, file_content=event_copy.text, filename="Bot reply.txt", title="Automated User Input", is_internal=True)
        else:
            await self.user_interaction_dispatcher.send_message(event=event_copy, message=f"AutomatedUserInput: {event_copy.text}", message_type=MessageType.TEXT, is_internal=True)

        await self.global_manager.user_interactions_behavior_dispatcher.process_incoming_notification_data(event_copy)

    async def trigger_feedback(self, event: IncomingNotificationDataBase) -> Any:
        try:
            user_feedback = event.text
            self.logger.info(f"Received feedback from user {event.user_id}: {user_feedback}")

            response_message = "Thank you for your feedback!"
            await self.user_interaction_dispatcher.send_message(
                event=event,
                message=response_message,
                message_type=MessageType.TEXT
            )

            return {"status": "feedback_received", "feedback": user_feedback}

        except Exception as e:
            self.logger.error(f"Error in processing feedback: {e}")
            raise
    
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
            