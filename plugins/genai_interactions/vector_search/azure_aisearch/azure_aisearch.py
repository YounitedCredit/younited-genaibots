import inspect
import json

import aiohttp
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class OpenAIRequestError(Exception):
    def __init__(self, status_code, response_body):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"OpenAI request failed with status code {status_code}")


class AzureAisearchConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_AISEARCH_AZURE_OPENAI_KEY: str
    AZURE_AISEARCH_AZURE_OPENAI_ENDPOINT: str
    AZURE_AISEARCH_OPENAI_API_VERSION: str
    AZURE_AISEARCH_MODEL_NAME: str
    AZURE_AISEARCH_SEARCH_ENDPOINT: str
    AZURE_AISEARCH_KEY: str
    AZURE_AISEARCH_INDEX_NAME: str
    AZURE_AISEARCH_TOPN_DOCUMENT: int
    AZURE_AISEARCH_TEXT_COMPLETION_MODEL_NAME: str
    AZURE_AISEARCH_PROMPT: str


class AzureAisearchPlugin(GenAIInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = global_manager.logger
        azure_aisearch_config_dict = \
        global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH["AZURE_AISEARCH"]
        self.azure_aisearch_config = AzureAisearchConfig(**azure_aisearch_config_dict)
        self.plugin_name = None

    def initialize(self):
        self.azure_openai_key = self.azure_aisearch_config.AZURE_AISEARCH_AZURE_OPENAI_KEY
        self.azure_openai_endpoint = self.azure_aisearch_config.AZURE_AISEARCH_AZURE_OPENAI_ENDPOINT
        self.openai_api_version = self.azure_aisearch_config.AZURE_AISEARCH_OPENAI_API_VERSION
        self.model_name = self.azure_aisearch_config.AZURE_AISEARCH_MODEL_NAME
        self.search_endpoint = self.azure_aisearch_config.AZURE_AISEARCH_SEARCH_ENDPOINT
        self.search_key = self.azure_aisearch_config.AZURE_AISEARCH_KEY
        self.search_index_name = self.azure_aisearch_config.AZURE_AISEARCH_INDEX_NAME
        self.search_topn_document = self.azure_aisearch_config.AZURE_AISEARCH_TOPN_DOCUMENT
        self.search_completion_model_name = self.azure_aisearch_config.AZURE_AISEARCH_TEXT_COMPLETION_MODEL_NAME
        self.search_prompt = self.azure_aisearch_config.AZURE_AISEARCH_PROMPT
        self.plugin_name = self.azure_aisearch_config.PLUGIN_NAME

        self.client = AsyncAzureOpenAI(
            api_version=self.openai_api_version,
            azure_endpoint=self.azure_openai_endpoint,
            api_key=self.azure_openai_key,
        )

    @property
    def plugin_name(self):
        return "azure_aisearch"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    async def handle_request(self, event: IncomingNotificationDataBase):
        try:
            # Create an ActionInput with event.text as the prompt
            action_input = ActionInput(action_name="search", parameters={"input": event.text})

            # Send the ActionInput to handle_action
            result = await self.handle_action(action_input)
            return result
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return None

    def validate_request(self, event: IncomingNotificationDataBase):
        return True

    def trigger_genai(self, user_message=None, event: IncomingNotificationDataBase = None):
        raise NotImplementedError(
            f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase = None):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        query = parameters.get('query', '')  # The search query
        index_name = parameters.get('index_name',
                                    self.search_index_name).lower()  # Use provided index_name or fallback to default
        get_whole_doc = parameters.get('get_whole_doc', False)  # New flag for fetching full document

        # Check if index_name is empty
        if not index_name:
            error_message = "Index name is required but not provided."
            self.logger.error(error_message)
            raise ValueError(error_message)

        # Call search and handle fetching full document based on document_id
        result = await self.call_search(message=query, index_name=index_name, get_whole_doc=get_whole_doc)
        return result

    def prepare_search_body_headers(self, message):
        body = {
            "search": message,
            "top": self.search_topn_document,
            "select": "id, title, content, file_path",  # Return ID, title, content and file_path
            "queryType": "simple"  # Use 'simple' for a basic search
        }

        headers = {
            'Content-Type': 'application/json',
            'api-key': self.search_key
        }

        return body, headers

    async def post_request(self, endpoint, headers, body):
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=body) as response:
                status = response.status
                body = await response.read()
                return status, body

    async def call_search(self, message, index_name, get_whole_doc=False):
        try:
            # Perform the initial search query to retrieve passages
            search_url = f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version=2021-04-30-Preview"

            search_headers = {
                'Content-Type': 'application/json',
                'api-key': self.search_key
            }

            search_body = {
                "search": message,
                "top": self.search_topn_document,
                "select": "id, document_id, title, content, passage_id, file_path"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(search_url, headers=search_headers, json=search_body) as response:
                    status = response.status
                    body = await response.json()

                    if status != 200:
                        self.logger.error(f"Search failed with status code {status}")
                        raise OpenAIRequestError(status, body)

                    search_results = body.get("value", [])

                    # If get_whole_doc is True, replace the content of each result with the full document content
                    if get_whole_doc:
                        search_results = await self.replace_with_full_document_content(search_results, index_name)

                    return json.dumps({"search_results": search_results})

        except Exception as e:
            self.logger.error(f"An error occurred during search: {e}")
            return json.dumps({
                "response": [
                    {
                        "Action": {
                            "ActionName": "UserInteraction",
                            "Parameters": {
                                "value": "I was unable to retrieve the information."
                            }
                        }
                    }
                ]
            })

    async def replace_with_full_document_content(self, search_results, index_name):
        """Replace the content field with full document content for each result."""
        ids_seen = set()

        try:
            for result in search_results:
                document_id = result['document_id']

                # Fetch all passages for this document id if we haven't processed it yet
                if document_id not in ids_seen:
                    full_document_content = await self.fetch_full_document_content(document_id, index_name)
                    result['content'] = full_document_content  # Replace the content with the full document
                    ids_seen.add(document_id)  # Mark this document id as processed

            return search_results

        except Exception as e:
            self.logger.error(f"Error while fetching full document content: {e}")
            return search_results

    async def fetch_full_document_content(self, document_id, index_name):
        try:
            fetch_url = f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version=2021-04-30-Preview"
            fetch_headers = {
                'Content-Type': 'application/json',
                'api-key': self.search_key
            }
            fetch_body = {
                "filter": f"document_id eq '{document_id}'",
                "select": "content, passage_id",
                "top": 1000
            }

            status, response_body = await self.post_request(fetch_url, fetch_headers, fetch_body)

            self.logger.debug(f"Fetch status: {status}")
            self.logger.debug(f"Response body: {response_body}")

            if status != 200:
                self.logger.error(f"Failed to fetch full document with status {status}")
                return ""

            # Parse the JSON response
            fetch_body = json.loads(response_body)

            self.logger.debug(f"Parsed fetch body: {fetch_body}")

            # Collect and concatenate all passages by passage_id
            passages = sorted(fetch_body.get("value", []), key=lambda x: x['passage_id'])
            self.logger.debug(f"Sorted passages: {passages}")

            full_document_content = " ".join([passage['content'] for passage in passages])
            self.logger.debug(f"Full document content: {full_document_content}")

            return full_document_content

        except Exception as e:
            self.logger.error(f"Error while fetching full document: {e}")
            return ""
