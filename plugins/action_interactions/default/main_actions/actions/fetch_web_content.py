import copy
import re
import traceback
import urllib.parse

import aiohttp
from bs4 import BeautifulSoup

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.backend.backend_internal_data_processing_dispatcher import (
    BackendInternalDataProcessingDispatcher,
)
from core.genai_interactions.genai_interactions_text_dispatcher import (
    GenaiInteractionsTextDispatcher,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)


class FetchWebContent(ActionBase):
    REQUIRED_PARAMETERS = ['url']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interaction_dispatcher : UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher : GenaiInteractionsTextDispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher : BackendInternalDataProcessingDispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput , event: IncomingNotificationDataBase):

        try:
            parameters = action_input.parameters
            urls = parameters.get('url', '')

            if not urls:
                self.logger.error("No URL provided")
                await self.user_interaction_dispatcher.send_message(event=event, message="No URL provided", message_type=MessageType.COMMENT, is_internal=True)
                await self.user_interaction_dispatcher.send_message(event=event, message="Sorry, something went wrong, I didn't receive any url. Try again or contact the bot owner", message_type=MessageType.COMMENT)
                return

            urls = urls.split(',')  # split the urls by comma
            all_content = ""  # variable to store all content

            for url in urls:
                url = urllib.parse.unquote(url.strip())  # decode the url
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        text = await response.text()
                        soup = BeautifulSoup(text, 'html.parser')
                        content = soup.get_text()
                        cleaned_content = self.cleanup_webcontent(content)  # clean the content
                        all_content += f'Here is the content of the target url, use it to answer to the user as he won t see this response: {url}: {cleaned_content}\n'  # add cleaned content to all_content

            event_copy = copy.deepcopy(event)
            event_copy.images = []
            event_copy.files_content = []
            event_copy.text = all_content  # set event_copy.text to all_content
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")

    def cleanup_webcontent(self, text):
        text = text.replace('\n', '')
        text = text.replace('\r', '')
        text = text.replace('\t', '')
        text = text.replace('\'', "'")
        text = re.sub(' +', ' ', text)
        return text
