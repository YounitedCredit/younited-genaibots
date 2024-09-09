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
        query = parameters.get('query', '')  # The search query
        index_name = parameters.get('index_name', self.search_index_name).lower()  # Use provided index_name or fallback to default
        get_whole_doc = parameters.get('get_whole_doc', False)  # New flag for fetching full document

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
                "select": "id, title, content, passage_id"  # Fetch required fields including id, content, and passage_id
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(search_url, headers=search_headers, json=search_body) as response:
                    status = response.status
                    body = await response.json()

                    if status != 200:
                        self.logger.error(f"Search failed with status code {status}")
                        raise OpenAIRequestError(status, body)

                    # Process the search results
                    search_results = body.get("value", [])
                    if get_whole_doc and search_results:
                        # For each result, fetch all passages related to its id
                        full_documents = await self.fetch_all_documents(search_results, index_name)
                        return json.dumps({"full_documents": full_documents})

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

    async def fetch_all_documents(self, search_results, index_name):
        """Fetches all content and metadata for each unique document id in the search results."""
        full_documents = []
        ids_seen = set()

        try:
            for result in search_results:
                document_id = result['id']

                # Skip if we've already fetched this document
                if document_id in ids_seen:
                    continue

                # Fetch all passages for this id
                full_document_data = await self.fetch_full_document(document_id, index_name)
                ids_seen.add(document_id)  # Mark this document id as processed

                # Add the full document data to the final result
                full_documents.append({
                    "id": document_id,  # Group by id
                    "passages": full_document_data  # All passages (chunks) for this document
                })

            return full_documents

        except Exception as e:
            self.logger.error(f"Error while fetching documents: {e}")
            return []

    async def fetch_full_document(self, document_id, index_name):
        """Fetches all the passages for a specific document id."""
        try:
            fetch_url = f"{self.search_endpoint}/indexes/{index_name}/docs/search?api-version=2021-04-30-Preview"
            fetch_headers = {
                'Content-Type': 'application/json',
                'api-key': self.search_key
            }

            # Query all passages that share the same id
            fetch_body = {
                "filter": f"id eq '{document_id}'",  # Fetch all passages by id
                "select": "id, content, passage_id",  # Fetch content and passage_id
                "top": 1000  # Assuming the document won't exceed 1000 chunks
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(fetch_url, headers=fetch_headers, json=fetch_body) as response:
                    fetch_status = response.status
                    fetch_body = await response.json()

                    if fetch_status != 200:
                        self.logger.error(f"Failed to fetch full document with status {fetch_status}")
                        return []

                    # Collect all passages and metadata
                    passages = sorted(fetch_body.get("value", []), key=lambda x: x['passage_id'])
                    return [{
                        "passage_id": passage['passage_id'],
                        "content": passage['content'],
                    } for passage in passages]

        except Exception as e:
            self.logger.error(f"Error while fetching full document: {e}")
            return []