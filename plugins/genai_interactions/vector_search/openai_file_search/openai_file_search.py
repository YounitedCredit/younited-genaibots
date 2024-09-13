import inspect
import json
from typing import List

import numpy as np
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class OpenaiFileSearchConfig(BaseModel):
    PLUGIN_NAME: str
    OPENAI_FILE_SEARCH_OPENAI_KEY: str
    OPENAI_FILE_SEARCH_OPENAI_ENDPOINT: str
    OPENAI_FILE_SEARCH_OPENAI_API_VERSION: str
    OPENAI_FILE_SEARCH_MODEL_HOST: str  # Can be "azure" or "openai"
    OPENAI_FILE_SEARCH_MODEL_NAME: str
    OPENAI_FILE_SEARCH_RESULT_COUNT: int
    OPENAI_FILE_SEARCH_INDEX_NAME: str


class OpenaiFileSearchPlugin(GenAIInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = global_manager.logger
        openai_search_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH["OPENAI_FILE_SEARCH"]
        self.openai_search_config = OpenaiFileSearchConfig(**openai_search_config_dict)
        self._plugin_name = "openai_file_search"

    def initialize(self):
        if self.openai_search_config.OPENAI_FILE_SEARCH_MODEL_HOST.lower() == "azure":
            self.client = AsyncAzureOpenAI(
                api_key=self.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_KEY,
                azure_endpoint=self.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_ENDPOINT,
                api_version=self.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_API_VERSION
            )
        else:
            self.client = AsyncOpenAI(api_key=self.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_KEY)
        self.result_count = self.openai_search_config.OPENAI_FILE_SEARCH_RESULT_COUNT
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def validate_request(self, event: IncomingNotificationDataBase):
        return True

    async def handle_request(self, event: IncomingNotificationDataBase):
        action_input = ActionInput(action_name="search", parameters={"query": event.text})
        result = await self.handle_action(action_input, event)
        return result

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase = None):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        query = parameters.get('query', '')
        index_name = parameters.get('index_name', '').lower()
        result_count = parameters.get('result_count', self.result_count)
        get_whole_doc = parameters.get('get_whole_doc', False)  # New flag for fetching full document

        # Retrieve default index name from configuration if index_name is empty
        if not index_name:
            index_name = self.openai_search_config.OPENAI_FILE_SEARCH_INDEX_NAME.lower()

        # Check if index_name is still empty
        if not index_name:
            error_message = "Index name is required but not provided."
            self.logger.error(error_message)
            raise ValueError(error_message)

        result = await self.call_search(query=query, index_name=index_name, result_count=result_count, get_whole_doc=get_whole_doc)
        return result

    async def call_search(self, query, index_name, result_count, get_whole_doc=False):
        try:
            file_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container="vectors", data_file=f"{index_name}.json")
            data = json.loads(file_content)
        except Exception as e:
            self.logger.error(f"Failed to load JSON file: {str(e)}")
            return json.dumps({"error": "Failed to load search data."})

        if not data.get('value', []):
            return json.dumps({"search_results": []})

        query_embedding = await self.get_embedding(query, model=self.openai_search_config.OPENAI_FILE_SEARCH_MODEL_NAME)

        for item in data['value']:
            item['similarity'] = self.cosine_similarity(np.array(item['vector']), query_embedding)

        sorted_data = sorted(data['value'], key=lambda x: x['similarity'], reverse=True)[:result_count]

        # Fetch the whole document content if needed
        if get_whole_doc:
            sorted_data = await self.replace_with_full_document_content(sorted_data, index_name)

        search_results = [{
            "id": item['id'],
            "document_id": item['document_id'],
            "title": item.get('title', ''),
            "content": item.get('content', ''),
            "file_path": item.get('file_path', ''),
            "@search.score": item['similarity']
        } for item in sorted_data]

        return json.dumps({"search_results": search_results})

    async def replace_with_full_document_content(self, search_results, index_name):
        """Replace the content field with full document content for each result."""
        ids_seen = set()

        try:
            for result in search_results:
                document_id = result['document_id']

                if document_id not in ids_seen:
                    full_document_content = await self.fetch_full_document_content(document_id, index_name)
                    result['content'] = full_document_content  # Replace the content with the full document
                    ids_seen.add(document_id)

            return search_results

        except Exception as e:
            self.logger.error(f"Error while fetching full document content: {e}")
            return search_results

    async def fetch_full_document_content(self, document_id, index_name):
        """Fetches and concatenates all passages for a specific document id."""
        try:
            file_content = await self.backend_internal_data_processing_dispatcher.read_data_content("vectors", f"{index_name}.json")
            data = json.loads(file_content)

            passages = [item for item in data['value'] if item['document_id'] == document_id]
            passages = sorted(passages, key=lambda x: x['passage_id'])
            full_document_content = " ".join([passage['content'] for passage in passages])
            return full_document_content

        except Exception as e:
            self.logger.error(f"Error while fetching full document: {e}")
            return ""

    async def get_embedding(self, text: str, model: str) -> List[float]:
        text = text.replace("\n", " ")
        response = await self.client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    @property
    def plugin_name(self):
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def trigger_genai(self, user_message=None, event: IncomingNotificationDataBase = None):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")
