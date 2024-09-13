import inspect
import json

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


class AzureChatGptConfig(BaseModel):
    PLUGIN_NAME: str
    AZURE_DALLE_OPENAI_KEY: str
    AZURE_DALLE_OPENAI_ENDPOINT: str
    AZURE_DALLE_OPENAI_API_VERSION: str
    AZURE_DALLE_IMAGE_GENERATOR_MODEL_NAME: str
    AZURE_DALLE_INPUT_TOKEN_PRICE: float
    AZURE_DALLE_OUTPUT_TOKEN_PRICE: float

class AzureDallePlugin(GenAIInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        azure_dalle_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.IMAGE["AZURE_DALLE"]
        self.azure_chatgpt_config = AzureChatGptConfig(**azure_dalle_config_dict)
        self.logger = global_manager.logger
        self.plugin_name = None

    def initialize(self):
        self.azure_openai_key = self.azure_chatgpt_config.AZURE_DALLE_OPENAI_KEY
        self.azure_openai_endpoint = self.azure_chatgpt_config.AZURE_DALLE_OPENAI_ENDPOINT
        self.openai_api_version = self.azure_chatgpt_config.AZURE_DALLE_OPENAI_API_VERSION
        self.model_name = self.azure_chatgpt_config.AZURE_DALLE_IMAGE_GENERATOR_MODEL_NAME
        self.plugin_name = self.azure_chatgpt_config.PLUGIN_NAME

        self.client = AsyncAzureOpenAI(
            api_version =  self.openai_api_version,
            azure_endpoint= self.azure_openai_endpoint,
            api_key= self.azure_openai_key,
        )

    @property
    def plugin_name(self):
        return "azure_dalle"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def handle_request(self, event: IncomingNotificationDataBase):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    def validate_request(self, event: IncomingNotificationDataBase):
        return True

    def trigger_genai(self, event: IncomingNotificationDataBase):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def handle_action(self, action_input:ActionInput, event: IncomingNotificationDataBase = None):
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        prompt = parameters.get('prompt')
        size = parameters.get('size')

        try:
            result = await self.client.images.generate(
                model="dall-e-3", # the name of your DALL-E 3 deployment
                prompt=prompt,
                n=1,
                size=size
            )

            image_url = json.loads(result.model_dump_json())['data'][0]['url']
            return image_url
        except Exception as e:
            self.logger.error(f"Error generating image: {e}")
            self.logger.error(f"Parameters: prompt={prompt}, size={size}")
            return str(e)
