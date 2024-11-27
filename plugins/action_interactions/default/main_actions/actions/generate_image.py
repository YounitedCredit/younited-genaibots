import re

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class GenerateImage(ActionBase):
    REQUIRED_PARAMETERS = ['prompt', 'size']

    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.user_interactions_text_plugin = None
        self.logger = self.global_manager.logger

        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.genai_image_generator_dispatcher = self.global_manager.genai_image_generator_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            await self.user_interaction_dispatcher.send_message(event=event,
                                                                message="Generating your image please wait...",
                                                                message_type=MessageType.COMMENT, is_internal=False)
            target = action_input.parameters.get('target', '')
            url = await self.genai_image_generator_dispatcher.handle_action(action_input)
            if url:
                if "Error" in url:  # Check if the returned value is an error message
                    self.logger.error(f"An error occurred: {url}")
                    match = re.search(r"'message': '(.*?)'", url)
                    if match:
                        extracted_message = match.group(1)
                    else:
                        extracted_message = url
                    await self.user_interaction_dispatcher.send_message(event=event,
                                                                        message=f"Image generation failed: {extracted_message}",
                                                                        action_ref="generate_image")
                    await self.user_interaction_dispatcher.send_message(event=event,
                                                                        message=f"Image generation failed: {url}",
                                                                        is_internal=True)
                elif self.is_valid_url(url):  # Check if the returned value is a valid URL
                    if (target == "slack"):
                        await self.user_interaction_dispatcher.send_message(event=event, message=f"<{url}|Image>")
                    else:
                        await self.user_interaction_dispatcher.send_message(event=event, message=f"{url}")
                else:
                    await self.user_interaction_dispatcher.send_message(event=event,
                                                                        message=f"Image generation failed: Invalid URL {url}",
                                                                        action_ref="generate_image")
                    await self.user_interaction_dispatcher.send_message(event=event,
                                                                        message=f"Image generation failed: Invalid URL {url}",
                                                                        is_internal=True)
            else:
                await self.user_interaction_dispatcher.send_message(event=event, message="Image generation failed",
                                                                    action_ref="generate_image")
                await self.user_interaction_dispatcher.send_message(event=event, message="Image generation failed",
                                                                    is_internal=True)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")

    def is_valid_url(self, url):
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None
