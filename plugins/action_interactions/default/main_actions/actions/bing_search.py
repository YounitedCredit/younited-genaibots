import copy
import os
import re

import requests
from bs4 import BeautifulSoup

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType

# IMPORTANT : Define an environment variable for your subscription ID called BING_SEARCH_SUBSCRIPTION_KEY

class BingSearch(ActionBase):
    REQUIRED_PARAMETERS = ['query', "result_number", "from_snippet", "user_input", "urls"]
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager

        #Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

        self.logger = self.global_manager.logger
        self.subscription_key = os.getenv("BING_SEARCH_SUBSCRIPTION_KEY")
        self.search_url = "https://api.bing.microsoft.com/v7.0/search"

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        await self.user_interactions_dispatcher.send_message(event=event, message="Looking for more info on the web please wait...", message_type=MessageType.COMMENT, is_internal=False, action_ref="bing_search")

        query, result_number, from_snippet, user_input, urls = self.extract_parameters(action_input)

        if urls:
            await self.process_urls(urls, event)
            return

        search_results = await self.perform_search(query, event)

        if search_results is not None:
            await self.process_search_results(search_results, event, result_number, from_snippet, user_input)

    def extract_parameters(self, action_input):
        query = action_input.parameters.get('query', '')
        result_number = action_input.parameters.get('result_number', 1)
        from_snippet = action_input.parameters.get('from_snippet', False)
        from_snippet = self.parse_from_snippet(from_snippet)
        user_input = action_input.parameters.get('user_input', '')
        urls = action_input.parameters.get('urls', '')
        return query, result_number, from_snippet, user_input, urls

    def parse_from_snippet(self, from_snippet):
        if from_snippet is None:
            return False
        if isinstance(from_snippet, str):
            return from_snippet.lower() != 'false'
        return bool(from_snippet)

    async def perform_search(self, query, event):
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        params = {"q": query, "textDecorations": True, "textFormat": "Raw"}
        try:
            response = requests.get(self.search_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            await self.handle_search_error(e, event)
            return None

    async def handle_search_error(self, error, event):
        message = "An unknown error occurred."
        if isinstance(error, requests.exceptions.HTTPError):
            if error.response.status_code == 403:
                message = f"403 Forbidden error for URL: {self.search_url}. Skipping this URL."
            elif error.response.status_code == 401:
                message = f"401 Unauthorized error for URL: {self.search_url}. Permission denied."
            else:
                message = f"HTTPError for URL: {self.search_url}. Status code: {error.response.status_code}."
        elif isinstance(error, requests.exceptions.ConnectionError):
            message = f"ConnectionError for URL: {self.search_url}. Could not connect to the server."
        elif isinstance(error, requests.exceptions.Timeout):
            raise error
        self.logger.error(message)
        await self.user_interactions_dispatcher.send_message(event=event, message=message, message_type=MessageType.COMMENT, is_internal=True)
        await self.user_interactions_dispatcher.send_message(event=event, message=f"Oops something goes wrong! {message}", message_type=MessageType.COMMENT, is_internal=False, action_ref="bing_search")

    async def process_search_results(self, search_results, event, result_number, from_snippet, user_input):
        if 'webPages' in search_results and 'value' in search_results['webPages']:
            result_urls = [result['url'] for result in search_results['webPages']['value'][:result_number]]
        else:
            result_urls = []

        if from_snippet:
            await self.select_from_snippet(search_results=search_results, event=event, result_number=result_number, user_input=user_input)
        else:
            await self.get_webpages_content(result_urls, event)

    async def process_urls(self, urls, event:IncomingNotificationDataBase):
        event_copy = copy.deepcopy(event)
        urls_msg = []
        urls = urls.split(',')
        for url in urls:
            if not self.is_valid_url(url):
                await self.user_interactions_dispatcher.send_message(event=event, message=f"Sorry the url {url} is not valid", message_type=MessageType.COMMENT, is_internal=False, action_ref="bing_search")
                return
            else:
                page_content = await self.get_page_content(url)
                page_content = self.cleanup_webcontent(page_content)
                urls_msg.append(f"Here is the content of url {url} : {page_content}\n")

        event_copy.images = []
        event_copy.files_content = []
        if urls_msg:
            all_msgs = "\n".join(urls_msg)

            # text cleanup
            all_msgs = self.cleanup_webcontent(all_msgs)
            event_copy.text = f"Here is the content of all web pages detailed: {all_msgs}"
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
        else:
            event_copy.text = "Sorry the web content request returned no result. Please try rephrasing your request."
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)

    async def get_page_content(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"An unexpected error occurred for URL: {url}. Error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred for URL: {url}. Error: {str(e)}")
            return None

    def is_valid_url(self, url):
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None

    async def get_webpages_content(self, result_urls, event:IncomingNotificationDataBase):
        # Initialize a list to store the page contents
        page_contents = []

        # Iterate over the result URLs
        for url in result_urls:
            page_content = await self.get_page_content(url)
            if page_content is not None:
                page_contents.append(page_content)
            else:
                await self.user_interactions_dispatcher.send_message(
                    event=event,
                    message=f"An error occurred while fetching content from {url}.",
                    message_type=MessageType.COMMENT,
                    is_internal=True
                )

        # If we didn't get any page contents, send a message to the user
        if len(page_contents) < 1:
            await self.user_interactions_dispatcher.send_message(
                event=event,
                message="Sorry, we couldn't find a solution to your problem. Please try rephrasing your request.",
                message_type=MessageType.COMMENT,
                is_internal=False,
                action_ref="bing_search"
            )
            return
        else:
            # Ajout d'un message de succès
            await self.user_interactions_dispatcher.send_message(
                event=event,
                message=f"Successfully retrieved content from {len(page_contents)} web page(s).",
                message_type=MessageType.COMMENT,
                is_internal=True
            )

        page_messages = []

        # Add the first part of the message
        page_messages.append(f"Here is a text content from the {len(page_contents)} web page(s) we analyzed:")

        # Iterate over the page contents
        for i, page_content in enumerate(page_contents):
            # Create a message for this page
            page_message = f"{result_urls[i]} {page_content}"

            # Add the page message to the list
            page_messages.append(page_message)

        # Add the final part of the message
        page_messages.append("Process this to answer the user, mention the webpage(s) as a Slack link")
        event_copy = copy.deepcopy(event)
        # Join the page messages into a single string
        event_copy.text = "\n".join(page_messages)

        # text cleanup
        event_copy.text = self.cleanup_webcontent(event_copy.text)

        event_copy.images = []
        event_copy.files_content = []
        await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)

    def cleanup_webcontent(self, text):
        text = text.replace('\n', '')
        text = text.replace('\r', '')
        text = re.sub(' +', ' ', text)
        return text

    async def select_from_snippet(self, search_results, event : IncomingNotificationDataBase, result_number, user_input):
        # Initialize a list to store the page messages
        page_messages = []

        # Iterate over the search results
        for result in search_results['webPages']['value']:
            # Get the URL and snippet
            url = result['url']
            snippet = result['snippet']

            # Create a message for this result
            page_message = f"Here's webpage url {url} with a snippet of the content: {snippet}"

            # Add the page message to the list
            page_messages.append(page_message)
        event_copy = copy.deepcopy(event)
        event_copy.images = []
        event_copy.files_content = []
        # Join the page messages into a single string
        event_copy.text = (
            "\n".join(page_messages)
            + f" Here's the question of the user : {user_input} ."
            + f" Select up to {result_number} result that are the most relevant url"
            + " and create an action called 'GetContentFromUrls' with a parameter 'urls'"
            + " where you put all the url as a comma delimited value,"
            + f" and result_number set to {result_number},"
            + f" user_input with '{user_input}'"
            + " dont create a userinteraction before our next action wait for the result."
        )

        # Trigger the user event
        await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
