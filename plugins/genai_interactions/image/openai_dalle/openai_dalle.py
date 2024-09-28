import inspect
import json
import traceback

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import GenAIInteractionsPluginBase
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import IncomingNotificationDataBase


class OpenaiDalleConfig(BaseModel):
    PLUGIN_NAME: str
    OPENAI_DALLE_API_KEY: str
    OPENAI_DALLE_MODEL_NAME: str
    OPENAI_DALLE_INPUT_TOKEN_PRICE: float
    OPENAI_DALLE_OUTPUT_TOKEN_PRICE: float


class OpenaiDallePlugin(GenAIInteractionsPluginBase):
    def __init__(self, global_manager: GlobalManager):
        super().__init__(global_manager)
        self.global_manager = global_manager
        openai_dalle_config_dict = global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.IMAGE["OPENAI_DALLE"]
        self.openai_dalle_config = OpenaiDalleConfig(**openai_dalle_config_dict)
        self.logger = global_manager.logger
        self.plugin_name = None
        self.client = None

    def initialize(self):
        self.openai_api_key = self.openai_dalle_config.OPENAI_DALLE_API_KEY
        self.model_name = self.openai_dalle_config.OPENAI_DALLE_MODEL_NAME
        self.plugin_name = self.openai_dalle_config.PLUGIN_NAME

        # Set up OpenAI client
        self.client = AsyncOpenAI(api_key=self.openai_api_key)

    @property
    def plugin_name(self):
        return "openai_dalle"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def handle_request(self, event: IncomingNotificationDataBase):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    def validate_request(self, event: IncomingNotificationDataBase):
        return True

    def trigger_genai(self, event: IncomingNotificationDataBase):
        raise NotImplementedError(f"{self.__class__.__name__}.{inspect.currentframe().f_code.co_name} is not implemented")

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase = None):
        """
        Handle the action input and generate an image based on the prompt and size.
        """
        parameters = {k.lower(): v for k, v in action_input.parameters.items()}
        prompt = parameters.get('prompt')
        size = parameters.get('size', '1024x1024')  # Default to 1024x1024 if size is not provided

        try:
            self.logger.info(f"Generating image with prompt: {prompt}, size: {size}")

            # Call OpenAI DALL-E API to generate the image
            result = await self.client.images.generate(
                model=self.model_name,
                prompt=prompt,
                n=1,
                size=size
            )

            image_url = json.loads(result.model_dump_json())['data'][0]['url']
            self.logger.info(f"Image generated successfully: {image_url}")
            return image_url

        except Exception as e:
            error_trace = traceback.format_exc()
            self.logger.error(f"Error generating image: {e}\n{error_trace}")
            self.logger.error(f"Parameters: prompt={prompt}, size={size}")
            return str(e)

