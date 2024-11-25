import asyncio
import inspect
import json
import traceback
import uuid
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
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


class AzureLlama370bConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_LLAMA370B_INPUT_TOKEN_PRICE: float
    AZURE_LLAMA370B_OUTPUT_TOKEN_PRICE: float
    AZURE_LLAMA370B_KEY: str
    AZURE_LLAMA370B_ENDPOINT: str
    AZURE_LLAMA370B_MODELNAME: str

class AzureLlama370bPlugin(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.config_manager : ConfigManager = global_manager.config_manager
        azure_llama370b_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT["AZURE_LLAMA370B"]
        self.azure_llama370b_config = AzureLlama370bConfig(**azure_llama370b_config_dict)
        self.plugin_name = None
        self._genai_cost_base = None
        self.model_name = self.azure_llama370b_config.AZURE_LLAMA370B_MODELNAME

        # Dispatchers
        self.user_interaction_dispatcher = None
        self.genai_interactions_text_dispatcher = None
        self.backend_internal_data_processing_dispatcher = None

    @property
    def plugin_name(self):
        return "azure_llama370b"

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
        self.azure_llama370b_key = self.azure_llama370b_config.AZURE_LLAMA370B_KEY
        self.azure_llama370b_endpoint = self.azure_llama370b_config.AZURE_LLAMA370B_ENDPOINT
        self.azure_llama370b_modelname = self.azure_llama370b_config.AZURE_LLAMA370B_MODELNAME
        self.input_token_price = self.azure_llama370b_config.AZURE_LLAMA370B_INPUT_TOKEN_PRICE
        self.output_token_price = self.azure_llama370b_config.AZURE_LLAMA370B_OUTPUT_TOKEN_PRICE
        self.plugin_name = self.azure_llama370b_config.PLUGIN_NAME

        self.load_client()
        self.input_handler = ChatInputHandler(self.global_manager, self)
        self.input_handler.initialize()

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher : BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.session_manager_dispatcher: SessionManagerDispatcher = self.global_manager.session_manager_dispatcher

    def load_client(self):
        try:
            self.commandr_client = AsyncOpenAI(
                base_url=self.azure_llama370b_endpoint, api_key=self.azure_llama370b_key
            )
        except KeyError as e:
            self.logger.error(f"Missing configuration key: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Invalid configuration value: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while loading Azure Llama370b client: {e}")
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
                "model_name": self.azure_llama370b_modelname,
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

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase, raw_output=False):
        self.logger.info("Generate completion triggered...")

        # Filtrer les images si non nécessaires
        messages = await self.filter_images(messages)

        # Préparer les messages avant de les envoyer au modèle
        messages = [{'role': message.get('role'), 'content': message.get('content')} for message in messages]

        try:
            # Appel au modèle Generative AI pour générer la réponse
            completion = await self.commandr_client.chat.completions.create(
                model=self.azure_llama370b_modelname,
                messages=messages,
                temperature=0.1,
                top_p=0.1,
            )

            # Extraction de la réponse complète
            response = completion.choices[0].message.content

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

            # Extraction des détails sur l'utilisation des tokens et les coûts
            self.genai_cost_base = GenAICostBase()
            self.genai_cost_base.total_tk = completion.usage.total_tokens
            self.genai_cost_base.prompt_tk = completion.usage.prompt_tokens
            self.genai_cost_base.completion_tk = completion.usage.completion_tokens
            self.genai_cost_base.input_token_price = self.input_token_price
            self.genai_cost_base.output_token_price = self.output_token_price

            return response, self.genai_cost_base

        except asyncio.exceptions.CancelledError:
            await self.user_interaction_dispatcher.send_message(
                event=event_data,
                message="Task was cancelled",
                message_type=MessageType.COMMENT,
                is_internal=True
            )
            self.logger.error("Task was cancelled")
            raise

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")
            await self.user_interaction_dispatcher.send_message(
                event=event_data,
                message="An unexpected error occurred",
                message_type=MessageType.ERROR,
                is_internal=True
            )
            raise

    async def trigger_genai(self, event :IncomingNotificationDataBase):
            event_copy = event
            AUTOMATED_RESPONSE_TRIGGER = "AUTOMATED_RESPONSE"
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
