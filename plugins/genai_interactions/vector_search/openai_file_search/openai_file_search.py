import inspect
import traceback
from ast import literal_eval
from io import StringIO
from typing import List

import numpy as np
import pandas as pd
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.backend.internal_data_processing_base import InternalDataProcessingBase
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class OpenaiFileSearchConfig(BaseModel):
    PLUGIN_NAME: str
    OPENAI_SEARCH_OPENAI_KEY: str
    OPENAI_SEARCH_OPENAI_ENDPOINT: str
    OPENAI_SEARCH_OPENAI_API_VERSION: str
    OPENAI_SEARCH_MODEL_HOST : str
    OPENAI_SEARCH__MODEL_NAME: str
    OPENAI_SEARCH_INPUT_TOKEN_PRICE: float
    OPENAI_SEARCH_OUTPUT_TOKEN_PRICE: float
    OPENAI_SEARCH_CONTEXT_EXTRACTION: bool
    OPENAI_SEARCH_CONTEXT_EXTRACTION_BEFORE_RATIO: float
    OPENAI_SEARCH_CONTEXT_EXTRACTION_AFTER_RATIO: float
    OPENAI_SEARCH_TEXT_WEIGHT: float
    OPENAI_SEARCH_TITLE_WEIGHT: float
    OPENAI_SEARCH_USE_TITLE_IN_SEARCH: bool
    OPENAI_SEARCH_RESULT_COUNT: int

class OpenaiFileSearchPlugin(GenAIInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        self.logger = global_manager.logger
        openai_search_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH["OPENAI_FILE_SEARCH"]
        self.openai_search_config = OpenaiFileSearchConfig(**openai_search_config_dict)
        self.plugin_name = None

    def initialize(self):
        self.openai_key = self.openai_search_config.OPENAI_SEARCH_OPENAI_KEY
        self.openai_endpoint = self.openai_search_config.OPENAI_SEARCH_OPENAI_ENDPOINT
        self.openai_api_version = self.openai_search_config.OPENAI_SEARCH_OPENAI_API_VERSION
        self.model_name = self.openai_search_config.OPENAI_SEARCH__MODEL_NAME
        self.model_host = self.openai_search_config.OPENAI_SEARCH_MODEL_HOST
        self.input_token_price = self.openai_search_config.OPENAI_SEARCH_INPUT_TOKEN_PRICE
        self.output_token_price = self.openai_search_config.OPENAI_SEARCH_OUTPUT_TOKEN_PRICE
        self.context_extraction = self.openai_search_config.OPENAI_SEARCH_CONTEXT_EXTRACTION
        self.before_ratio = self.openai_search_config.OPENAI_SEARCH_CONTEXT_EXTRACTION_BEFORE_RATIO
        self.after_ratio = self.openai_search_config.OPENAI_SEARCH_CONTEXT_EXTRACTION_AFTER_RATIO
        self.text_weight = self.openai_search_config.OPENAI_SEARCH_TEXT_WEIGHT
        self.title_weight = self.openai_search_config.OPENAI_SEARCH_TITLE_WEIGHT
        self.use_title_in_search = self.openai_search_config.OPENAI_SEARCH_USE_TITLE_IN_SEARCH
        self.result_count = self.openai_search_config.OPENAI_SEARCH_RESULT_COUNT
        self.backend_internal_data_processing_dispatcher : InternalDataProcessingBase = self.global_manager.backend_internal_data_processing_dispatcher

        if self.model_host.lower() == "azure":
            self.client = AsyncAzureOpenAI(
                api_version =  self.openai_api_version,
                azure_endpoint= self.openai_endpoint,
                api_key= self.openai_key,
            )
        elif self.model_host.lower() == "openai":
            self.client = AsyncOpenAI(
                api_key= self.openai_key
            )

    @property
    def plugin_name(self):
        return "openai_file_search"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def validate_request(self, event: IncomingNotificationDataBase):
        return True

    async def handle_request(self, event: IncomingNotificationDataBase):
        action_input = ActionInput(action_name="search", parameters={"query": event.text})
        result = await self.handle_action(action_input, event)
        return result  # Assurez-vous de renvoyer une valeur

    async def handle_action(self, action_input:ActionInput, event: IncomingNotificationDataBase):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        query = parameters.get('query', '')
        self.index_name = parameters.get('index_name', '')
        self.result_count = parameters.get('result_count', self.result_count)
        result = await self.call_search(query=query, index_name=self.index_name, result_count=self.result_count)
        return result

    def trigger_genai(self, user_message = None, event: IncomingNotificationDataBase = None):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def call_search(self, query, index_name, result_count = 3, use_title_in_search = False, get_all_document = False):
        vector_container = self.backend_internal_data_processing_dispatcher.vectors
        try:
            file_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=vector_container, data_file=index_name)
            df = pd.read_csv(StringIO(file_content))
        except Exception:
            self.logger.error(f"Failed to load CSV file: {traceback.format_exc()}")
            raise

        if df.empty:
            return []  # Retourne une liste vide si le DataFrame est vide

        passage_indices = df['passage_index'].tolist()
        results = await self.search_reviews(df, query, passage_indices[0])
        return results

    async def get_embedding(self,text: str, model, **kwargs) -> List[float]:
        # replace newlines, which can negatively affect performance.
        text = text.replace("\n", " ")
        response = await self.client.embeddings.create(input=[text], model=model, **kwargs)
        return response.data[0].embedding

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    # Function to search reviews in the database based on a query
    async def search_reviews(self, df, query, passage_index):
        try:
            query_embedding = await self.get_embedding(query, model=self.model_name)
        except Exception as e:
            self.logger.error(f"Unexpected error getting query embedding: {e}")
            return []

        try:
            # Calculate similarity with text embeddings
            df['similarity_text'] = df['embedding'].apply(lambda x: self.cosine_similarity(np.array(literal_eval(x)), query_embedding))

            if self.use_title_in_search:
                # Calculate similarity with title embeddings
                df['similarity_title'] = df['title_embedding'].apply(lambda x: self.cosine_similarity(np.array(literal_eval(x)), query_embedding))
                # Combine similarities
                df['similarity'] = self.text_weight * df['similarity_text'] + self.title_weight * df['similarity_title']
            else:
                df['similarity'] = df['similarity_text']

            # Sort results by similarity
            res = df.sort_values('similarity', ascending=False).head(self.result_count)

            results = []
            for _, row in res.iterrows():
                document_id = row['document_id']
                passage_id = row['passage_id']
                similarity = row['similarity']
                text = row['text']
                title = row['title']
                file_path = row['file_path']
                # passage_index is already retrieved from the DataFrame

                if self.context_extraction:
                    context = await self.extract_context(self.index_name, document_id, passage_index, len(text))
                    text = context  # Use the extracted context as the text

                results.append((document_id, passage_id, similarity, text, title, file_path))

            return results
        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []

    # Function to extract context around a passage using passage index
    async def extract_context(self, index_name, document_id, passage_index, passage_length):
        try:
            full_content = await self.backend_internal_data_processing_dispatcher.read_data_content(data_container=index_name, data_file=document_id)

            context_length_before = int(passage_length * self.before_ratio)
            context_length_after = int(passage_length * self.after_ratio)

            context_start = max(passage_index - context_length_before, 0)
            context_end = min(passage_index + passage_length + context_length_after, len(full_content))

            context = full_content[context_start:context_end]

            return context
        except Exception as e:
            self.logger.error(f"Error during context extraction: {e}")
            return None



