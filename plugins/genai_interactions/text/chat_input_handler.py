
import asyncio
import json
import re
import traceback

import yaml

from core.backend.pricing_data import PricingData
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.message_type import MessageType
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)

from utils.config_manager.config_model import BotConfig
from utils.plugin_manager.plugin_manager import PluginManager


class ChatInputHandler():
    def __init__(self, global_manager: GlobalManager, chat_plugin: GenAIInteractionsTextPluginBase):
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.chat_plugin : GenAIInteractionsTextPluginBase = chat_plugin

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def initialize(self):
        self.genai_client = {}
        self.bot_config : BotConfig = self.global_manager.bot_config
        self.conversion_format = self.bot_config.LLM_CONVERSION_FORMAT

    async def handle_event_data(self, event_data: IncomingNotificationDataBase):
        try:
            if event_data.event_label == 'message':
                return await self.handle_message_event(event_data)
            elif event_data.event_label == 'thread_message':
                return await self.handle_thread_message_event(event_data)
        except Exception as e:
            self.logger.error(f"Error while handling event data: {e}")
            raise

    async def handle_message_event(self, event_data: IncomingNotificationDataBase):
        try:
            feedbacks_container = self.backend_internal_data_processing_dispatcher.feedbacks
            general_behavior_content = await self.backend_internal_data_processing_dispatcher.read_data_content(feedbacks_container, self.bot_config.FEEDBACK_GENERAL_BEHAVIOR)
            await self.global_manager.prompt_manager.initialize()
            init_prompt = f"{self.global_manager.prompt_manager.core_prompt}\n{self.global_manager.prompt_manager.main_prompt}"
            constructed_message = f"Timestamp: {str(event_data.converted_timestamp)}, [username]: {str(event_data.user_name)}, [user id]: {str(event_data.user_id)}, [user email]: {event_data.user_email}, [Directly mentioning you]: {str(event_data.is_mention)}, [message]: {str(event_data.text)}"

            if general_behavior_content:
                init_prompt += f"\nAlso take into account these previous general behavior feedbacks constructed with user feedback from previous plugins, take them as the prompt not another feedback to add: {str(general_behavior_content)}"

            messages = [{"role": "system", "content": init_prompt}]
            user_content_text = [{"type": "text", "text": constructed_message}]
            user_content_images = []

            if event_data.images:
                for base64_image in event_data.images:
                    image_message = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                    user_content_images.append(image_message)

            if event_data.files_content:
                for file_content in event_data.files_content:
                    file_message = {"type": "text", "text": file_content}
                    user_content_text.append(file_message)

                if len(event_data.files_content) > 20:
                    reminder_message = f"Remember to follow the core prompt rules: {init_prompt}"
                    user_content_text.append({"type": "text", "text": reminder_message})

            user_content = user_content_text + user_content_images
            messages.append({"role": "user", "content": user_content})

            return await self.generate_response(event_data, messages)
        except Exception as e:
            self.logger.error(f"Error while handling message event: {e}")
            raise

    async def handle_thread_message_event(self, event_data: IncomingNotificationDataBase):
        try:
            # Construct the blob name and retrieve the content
            blob_name = f"{event_data.channel_id}-{event_data.thread_id}.txt"
            sessions = self.backend_internal_data_processing_dispatcher.sessions
            messages = json.loads(await self.backend_internal_data_processing_dispatcher.read_data_content(sessions, blob_name) or "[]")

            # Add new message to the JSON
            constructed_message = {
                "role": "user",
                "content": f"Timestamp: {str(event_data.converted_timestamp)}, [Slack username]: {str(event_data.user_name)}, [Slack user id]: {str(event_data.user_id)}, [Slack user email]: {event_data.user_email}, [Directly mentioning you]: {str(event_data.is_mention)}, [message]: {str(event_data.text)}"
            }

            user_content_text = [{"type": "text", "text": constructed_message["content"]}]
            user_content_images = []

            if event_data.images:
                for base64_image in event_data.images:
                    image_message = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                    user_content_images.append(image_message)

            if event_data.files_content:
                for file_content in event_data.files_content:
                    file_message = {"type": "text", "text": file_content}
                    user_content_text.append(file_message)

            user_content = user_content_text + user_content_images
            messages.append({"role": "user", "content": user_content})

            if event_data.is_mention and self.global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE:
                # If bot is mentioned or require_mention_thread_message is true, retrieve and extend with previously stored messages
                messages.extend(await self.backend_internal_data_processing_dispatcher.retrieve_unmentioned_messages(event_data.channel_id, event_data.thread_id))
            elif event_data.is_mention == False and self.global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE:
                # If bot is not mentioned, store the message for later
                await self.backend_internal_data_processing_dispatcher.store_unmentioned_messages(event_data.channel_id, event_data.thread_id, constructed_message)
                return None

            if not event_data.images and not event_data.files_content:
                messages.append(constructed_message)

            return await self.generate_response(event_data, messages)
        except Exception as e:
            self.logger.error(f"Error while handling thread message event: {e}")
            raise

    async def generate_response(self, event_data: IncomingNotificationDataBase, messages):
        try:
            original_msg_ts = event_data.thread_id if event_data.thread_id else event_data.timestamp
            if event_data.is_mention or event_data.event_label == "message":
                self.logger.info("GENAI CALL: Calling Generative AI completion for user input..")
                await self.global_manager.user_interactions_behavior_dispatcher.begin_genai_completion(event_data, channel_id=event_data.channel_id, timestamp= event_data.timestamp)
                completion = await self.call_completion(event_data.channel_id,original_msg_ts, messages, event_data)
                await self.global_manager.user_interactions_behavior_dispatcher.end_genai_completion(event=event_data, channel_id=event_data.channel_id, timestamp= event_data.timestamp)
            return completion
        except Exception as e:
            self.logger.error(f"Error while generating response: {e}\n{traceback.format_exc()}")
            raise

    async def filter_messages(self, messages):
        filtered_messages = []
        for message in messages:
            # If the message is from the user and its content is a list, we filter out 'image_url' content.
            # This is because the GenAI model currently only supports text inputs, not images.
            if message['role'] == 'user' and isinstance(message['content'], list):
                filtered_content = [content for content in message['content'] if content['type'] != 'image_url']
                message['content'] = filtered_content
            filtered_messages.append(message)
        return filtered_messages

    async def call_completion(self, channel_id, thread_id, messages, event_data: IncomingNotificationDataBase):
        # Define blob_name for session storage
        blob_name = f"{channel_id}-{thread_id}.txt"

        try:
            completion, genai_cost_base = await self.chat_plugin.generate_completion(messages, event_data)
        except asyncio.exceptions.CancelledError:
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled", message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            return None
        except Exception as e:
            return await self.handle_completion_errors(event_data, e)

        self.logger.info("Completion from generative AI received")

        # Extract the Genai response
        costs = self.backend_internal_data_processing_dispatcher.costs

        await self.calculate_and_update_costs(genai_cost_base, costs, blob_name, event_data)

        gpt_response = completion.replace("[BEGINIMDETECT]", "").replace("[ENDIMDETECT]", "")

        # Log Genai response to appropriate channel
        await self.user_interaction_dispatcher.upload_file(event=event_data, file_content=gpt_response, filename="Genai_response_raw.yaml", title="Genai response YAML", is_internal=True)

        try:
            if self.conversion_format == "json":
                gpt_response = gpt_response.replace("\\\\n", "\\n")
                response_json = json.loads(gpt_response)
            elif self.conversion_format == "yaml":
                sanitized_yaml = self.adjust_yaml_structure(gpt_response)
                response_json = await self.yaml_to_json(event_data=event_data, yaml_string=sanitized_yaml)
            else:
                self.logger.warning(f"Invalid conversion format: {self.conversion_format}, trying to convert from JSON, expect failures!")
                response_json = json.loads(gpt_response)

        except Exception as e:
            await self.user_interaction_dispatcher.send_message(event=event_data, message=f"An error occurred while converting the completion: {e}", message_type=MessageType.COMMENT, is_internal=True)
            return None

        # Save the entire conversation to the session blob
        messages.append({"role": "assistant", "content": completion})
        completion_json = json.dumps(messages)
        sessions = self.backend_internal_data_processing_dispatcher.sessions
        self.logger.debug(f"conversation stored in {sessions} : {blob_name} ")
        await self.backend_internal_data_processing_dispatcher.write_data_content(sessions, blob_name, completion_json)
        return response_json

    async def handle_completion_errors(self, event_data, e):
        await self.user_interaction_dispatcher.send_message(event=event_data, message=f"An error occurred while calling the completion: {e}", message_type=MessageType.COMMENT, is_internal=True)
        error_message = str(e)
        start = error_message.find('\'message\': "') + 12
        end = error_message.find('", \'param\':', start)
        sanitized_message = error_message[start:end]
        sanitized_message = sanitized_message.replace('\\r\\n', ' ')
        await self.user_interaction_dispatcher.send_message(event=event_data, message=f":warning: Sorry, I was unable to analyze the content you provided: {sanitized_message}", message_type=MessageType.COMMENT, is_internal=False)
        self.logger.error(f"Failed to create completion: {e}")
        return None

    def adjust_yaml_structure(self, yaml_content):
        lines = yaml_content.split('\n')
        adjusted_lines = []
        inside_parameters_block = False
        multiline_literal_indentation = 0

        for line in lines:
            # If we're inside a multiline block, we check the indentation level
            if multiline_literal_indentation > 0 and not line.startswith(' ' * multiline_literal_indentation):
                # We've reached the end of the multiline block
                multiline_literal_indentation = 0

            stripped_line = line.strip()

            # Escape asterisks in the YAML string
            stripped_line = stripped_line.replace('*', '\\*')

            # No leading spaces for 'response:'
            if stripped_line.startswith('response:'):
                adjusted_lines.append(stripped_line)
                inside_parameters_block = False

            # 2 spaces before '- Action:'
            elif stripped_line.startswith('- Action:'):
                adjusted_lines.append('  ' + stripped_line)
                inside_parameters_block = False

            # 6 spaces before 'ActionName:' or 'Parameters:'
            elif stripped_line.startswith('ActionName:') or stripped_line.startswith('Parameters:'):
                adjusted_lines.append('      ' + stripped_line)
                inside_parameters_block = True

            # Starts a multiline value
            elif inside_parameters_block and stripped_line.endswith(': |'):
                adjusted_lines.append('        ' + stripped_line)
                multiline_literal_indentation = 8

            # Handle the lines within a multiline block
            elif multiline_literal_indentation > 0:
                # The line is part of a multiline block, keep its current indentation
                adjusted_lines.append(line)

            # Regular parameter value lines under 'Parameters:'
            elif inside_parameters_block and re.match(r"^\w+:", stripped_line):
                adjusted_lines.append('        ' + stripped_line)

            # Keep the original indentation for everything else
            else:
                adjusted_lines.append(line)

        # Reconstruct the adjusted YAML content
        adjusted_yaml_content = '\n'.join(adjusted_lines)
        return adjusted_yaml_content


    async def yaml_to_json(self, event_data, yaml_string):
        try:
            # Load the YAML string into a Python dictionary
            python_dict = yaml.safe_load(yaml_string)

            # Check if 'value' contains a YAML string and load it
            for action in python_dict['response']:
                if 'value' in action['Action']['Parameters']:
                    value_str = action['Action']['Parameters']['value']
                    if value_str.startswith('```yaml') and value_str.endswith('```'):
                        # Remove the markdown code block syntax
                        yaml_str = value_str[9:-3].strip()  # Adjusted to remove 'yaml' and the following space
                        # Remove leading and trailing newlines
                        yaml_str = yaml_str.strip('\n')
                        action['Action']['Parameters']['value'] = yaml.safe_load(yaml_str)

            return python_dict
        except Exception as e:
            self.logger.error(f"An error occurred while processing the YAML string: {str(e)}")
            self.logger.error(traceback.format_exc())
            await self.user_interaction_dispatcher.send_message(
                event=event_data,
                message=f"An error occurred while processing the YAML string: {str(e)}\nTraceback:\n{traceback.format_exc()}",
                message_type=MessageType.COMMENT,
                is_internal=True
            )
            await self.user_interaction_dispatcher.send_message(event=event_data, message="😓 Sorry something went wrong with this thread formatting. Create a new thread and try again! (consult logs for deeper infos)", message_type=MessageType.TEXT, is_internal=False)
            return None

    async def calculate_and_update_costs(self, cost_params: GenAICostBase, costs_blob_container_name, blob_name, event:IncomingNotificationDataBase):
        # Initialize total_cost, input_cost, and output_cost to 0
        total_cost = input_cost = output_cost = 0

        try:
            # Extract the GPT response and token usage details
            total_tk = cost_params.total_tk
            prompt_tk = cost_params.prompt_tk
            completion_tk = cost_params.completion_tk

            # Ensure prompt_tk and input_token_price are floats
            prompt_tk = float(prompt_tk)
            input_token_price = float(cost_params.input_token_price)
            output_token_price = float(cost_params.output_token_price)

            # Calculate the costs
            input_cost = (prompt_tk / 1000) * input_token_price
            output_cost = (completion_tk / 1000) * output_token_price
            total_cost = input_cost + output_cost

            # Update the cost in blob and get the cumulative cost details
            pricing_data = PricingData(total_tokens=total_tk, prompt_tokens=prompt_tk, completion_tokens=completion_tk, total_cost=total_cost, input_cost=input_cost, output_cost=output_cost)

            updated_pricing_data = await self.backend_internal_data_processing_dispatcher.update_pricing(container_name=costs_blob_container_name, datafile_name=blob_name, pricing_data=pricing_data)

            cost_update_msg = (
                f"🔹 Last: {total_tk} tk {total_cost:.2f}$ "
                f"[🔼 {input_cost:.2f}$ {prompt_tk} tk "
                f"🔽 {output_cost:.2f}$/{completion_tk} tk] | "
                f"💰 Total: {updated_pricing_data.total_cost:.2f}$ "
                f"[🔼 {updated_pricing_data.input_cost:.2f}$/{updated_pricing_data.prompt_tokens} tk "
                f"🔽 {updated_pricing_data.output_cost:.2f}$/{updated_pricing_data.completion_tokens} tk]"
            )

            if (self.global_manager.bot_config.SHOW_COST_IN_THREAD):
                await self.user_interaction_dispatcher.send_message(event=event, message=cost_update_msg, message_type=MessageType.COMMENT, is_internal=False, plugin_name=event.origin_plugin_name)
            else:
                await self.user_interaction_dispatcher.send_message(event=event, message=cost_update_msg, message_type=MessageType.COMMENT, is_internal=True, plugin_name=event.origin_plugin_name)

        except Exception as e:
            self.logger.error(f"An error occurred in method 'calculate_and_update_costs': {type(e).__name__}: {e}")

        return total_cost, input_cost, output_cost

