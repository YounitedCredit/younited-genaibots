from typing import Any, Dict, Optional

from pydantic import BaseModel


class BotConfig(BaseModel):
    CORE_PROMPT: str
    MAIN_PROMPT: str
    PROMPTS_FOLDER: str
    SUBPROMPTS_FOLDER: str
    FEEDBACK_GENERAL_BEHAVIOR: str
    REQUIRE_MENTION_NEW_MESSAGE : bool
    REQUIRE_MENTION_THREAD_MESSAGE : bool
    LOG_DEBUG_LEVEL : str
    LOAD_ACTIONS_FROM_BACKEND : bool
    SHOW_COST_IN_THREAD : bool
    ACKNOWLEDGE_NONPROCESSED_MESSAGE : bool
    GET_ALL_THREAD_FROM_MESSAGE_LINKS : bool
    GET_URL_CONTENT : bool
    ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME: str
    INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME: str
    USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME: str
    GENAI_TEXT_DEFAULT_PLUGIN_NAME: str
    GENAI_IMAGE_DEFAULT_PLUGIN_NAME: str
    GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME: str
    LLM_CONVERSION_FORMAT: str
    BREAK_KEYWORD: str
    START_KEYWORD: str

class LocalLogging(BaseModel):
    PLUGIN_NAME: str
    LOCAL_LOGGING_FILE_PATH: str

class AzureLogging(BaseModel):
    PLUGIN_NAME: str
    AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING: str

class Logging(BaseModel):
    LOCAL_LOGGING: Optional[LocalLogging] = None
    AZURE_LOGGING: Optional[AzureLogging] = None

class Environment(BaseModel):
    PLUGIN_NAME: str

class Utils(BaseModel):
    LOGGING: Logging

class Plugin(BaseModel):
    PLUGIN_NAME: str

class ActionInteractions(BaseModel):
    DEFAULT: Dict[str, Plugin] = {}
    CUSTOM: Dict[str, Plugin] = {}

class Backend(BaseModel):
    INTERNAL_DATA_PROCESSING: Dict[str, Any]

class UserInteractions(BaseModel):
    INSTANT_MESSAGING: Dict[str, Any]
    CUSTOM_API: Dict[str, Any]

class GenaiInteractions(BaseModel):
    TEXT: Dict[str, Any]
    IMAGE: Dict[str, Any]
    VECTOR_SEARCH: Dict[str, Any]

class UserInteractionsBehaviors(BaseModel):
    INSTANT_MESSAGING: Dict[str, Any]
    CUSTOM_API: Dict[str, Any]

class Plugins(BaseModel):
    ACTION_INTERACTIONS: ActionInteractions
    BACKEND: Backend
    USER_INTERACTIONS: UserInteractions
    USER_INTERACTIONS_BEHAVIORS: UserInteractionsBehaviors
    GENAI_INTERACTIONS: GenaiInteractions

class ConfigModel(BaseModel):
    BOT_CONFIG: BotConfig
    UTILS: Utils
    PLUGINS: Plugins


class SensitiveData(BaseModel):
    ENVIRONMENT: Environment
