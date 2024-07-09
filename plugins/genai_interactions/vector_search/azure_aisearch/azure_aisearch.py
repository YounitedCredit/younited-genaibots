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

    async def handle_action(self, action_input:ActionInput , event: IncomingNotificationDataBase = None):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        input_param = parameters.get('value', '')
        result = await self.call_search(message=input_param)
        return result
    
    def prepare_body_headers_with_data(self, message):
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "temperature": 0,
            "max_tokens": 4000,
            "top_p": 0,
            "stream": "true",
            "dataSources": []
        }
        # Set query type
        query_type = "vector"
       
        body["dataSources"].append(
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": self.search_endpoint,
                    "key": self.search_key,
                    "indexName": self.search_index_name,
                    "topNDocuments": self.search_topn_document,
                    "queryType": query_type,
                    "roleInformation": self.search_prompt,
                    "semanticConfiguration": "default"
                }
            })

        body["dataSources"][0]["parameters"]["embeddingDeploymentName"] = self.model_name

        headers = {
            'Content-Type': 'application/json',
            'api-key': self.azure_openai_key,
            "x-ms-useragent": "GitHubSampleWebApp/PublicAPI/3.0.0"
        }

        return body, headers

    async def post_request(self, endpoint, headers, body):
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, headers=headers, json=body) as response:
                status = response.status
                body = await response.read()
                return status, body
    
    async def call_search(self, message):
        try:
            body, headers = self.prepare_body_headers_with_data(message)
            if not self.azure_openai_endpoint.endswith('/'):
                self.azure_openai_endpoint += '/'

            endpoint = f"{self.azure_openai_endpoint}openai/deployments/{self.search_completion_model_name}/extensions/chat/completions?api-version={self.openai_api_version}"
            status, body = await self.post_request(endpoint, headers, body)
            if status != 200:
                self.logger.error(f"Request failed with status code {status}")
                self.logger.error(f"Response body: {str(body)}")
                raise OpenAIRequestError(status, body)
            
            body = json.loads(body.decode('utf-8'))
            try:
                messages = body["choices"][0]["messages"]
                citations_content = json.loads(messages[0]['content'])
                citations = {f"[doc{index}]": citation['title'] for index, citation in enumerate(citations_content['citations'])}

                content_to_modify = messages[1]['content']

                # Combine the message and citations into a single string
                bot_content = f"Message: {content_to_modify}\nCitations: {str(citations)}"
                return bot_content

            except KeyError:
                # Ce bloc est exécuté si une clé de l'objet message n'est pas trouvée.
                json_content = json.dumps({
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
                return json_content

        except Exception as e:
            # Ce bloc est exécuté pour toute autre exception qui pourrait survenir.
            self.logger.error(f"An error occurred during search: {e}")
            json_content = json.dumps({
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
            return json_content