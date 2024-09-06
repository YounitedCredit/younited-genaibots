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
    AZURE_AISEARCH_INPUT_TOKEN_PRICE: float
    AZURE_AISEARCH_OUTPUT_TOKEN_PRICE: float
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
        azure_aisearch_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH["AZURE_AISEARCH"]
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
            api_version =  self.openai_api_version,
            azure_endpoint= self.azure_openai_endpoint,
            api_key= self.azure_openai_key,
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
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase = None):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        query = parameters.get('query', '')  # The query to search for
        index_name = parameters.get('index_name', self.search_index_name).lower()  # Use provided index_name or fall back to default and convert to lower case
        result = await self.call_search(message=query, index_name=index_name)
        return result
    
    def prepare_search_body_headers(self, message):
        body = {
            "search": message,
            "top": self.search_topn_document,
            "select": "id, title, content",  # Return ID, title, and content
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
    
    async def call_search(self, message, index_name):
        try:
            # Prepare the search URL dynamically based on index_name
            search_url = f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version=2021-04-30-Preview"
            
            search_headers = {
                'Content-Type': 'application/json',
                'api-key': self.search_key
            }

            search_body = {
                "search": message,
                "select": "id, title, content",  # Fields to return
                "top": self.search_topn_document
            }

            # Perform the search request
            async with aiohttp.ClientSession() as session:
                async with session.post(search_url, headers=search_headers, json=search_body) as response:
                    status = response.status
                    body = await response.json()

                    # Check if search was successful
                    if status != 200:
                        self.logger.error(f"Search failed with status code {status}")
                        self.logger.error(f"Search response: {str(body)}")
                        raise OpenAIRequestError(status, body)

                    # Log and return the search results
                    search_results = body.get("value", [])
                    self.logger.info(f"Search returned {len(search_results)} results")
                    return json.dumps({"search_results": search_results})
                    
        except Exception as e:
            self.logger.error(f"An error occurred during search: {e}")
            return json.dumps({
                "response": [
                    {
                        "Action": {
                            "ActionName": "UserInteraction",
                            "Parameters": {
                                "value": "I was unable to gather the information in my data, sorry about that."
                            }
                        }
                    }
                ]
            })