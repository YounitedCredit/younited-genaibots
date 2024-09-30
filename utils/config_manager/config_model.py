from typing import Any, Dict, Optional

from pydantic import BaseModel


class BotConfig(BaseModel):
    # The name of the core prompt file (e.g., core_prompt.txt).
    CORE_PROMPT: str

    # The name of the main prompt file (e.g., main_prompt.txt).
    MAIN_PROMPT: str

    # The behavior feedback file, which handles general feedback behavior (e.g., "General_Global.txt").
    FEEDBACK_GENERAL_BEHAVIOR: str

    # If True, the bot requires a direct mention to respond to a new message in a channel.
    REQUIRE_MENTION_NEW_MESSAGE: bool

    # If True, the bot responds to thread messages even if not directly mentioned.
    REQUIRE_MENTION_THREAD_MESSAGE: bool

    # The logging level for the bot (e.g., "debug", "info", "warning", "error", "critical").
    LOG_DEBUG_LEVEL: str

    # If True, the bot loads actions from a backend, otherwise actions are local.
    LOAD_ACTIONS_FROM_BACKEND: bool

    # If True, the cost of interactions with the model will be shown directly in the conversation thread.
    SHOW_COST_IN_THREAD: bool

    # If True, the bot retrieves all thread messages linked to a specific message.
    GET_ALL_THREAD_FROM_MESSAGE_LINKS: bool

    # If True, the bot fetches and analyzes content from URLs found in user messages.
    GET_URL_CONTENT: bool

    # The default plugin name for handling action interactions, such as running specific commands or triggers.
    ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME: str

    # The default plugin for backend data processing (e.g., file system, Azure Blob Storage).
    INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME: str

    # The default plugin for internal queue processing (e.g., file system, Azure Service Bus, Azure Blob Storage).
    INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME: str

    # The default plugin for instant messaging behavior, which defines how the bot behaves in IM platforms (e.g., Slack or Teams).
    USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME: str

    # The default plugin for text generation (e.g., Azure OpenAI for text-based AI interactions).
    GENAI_TEXT_DEFAULT_PLUGIN_NAME: str

    # The default plugin for image generation (e.g., DALL-E for generating images based on text descriptions).
    GENAI_IMAGE_DEFAULT_PLUGIN_NAME: str

    # The default plugin for vector search (e.g., OpenAI File Search for vectorized content retrieval from large datasets).
    GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME: str

    # The format for the bot's responses (e.g., "json" or "yaml"). This defines how the bot structures its outputs.
    LLM_CONVERSION_FORMAT: str

    # The keyword used by the bot to identify when it should stop processing a message (e.g., "!STOP").
    BREAK_KEYWORD: str

    # The keyword used to start message processing (e.g., "!START"). Useful for controlling when the bot begins a task.
    START_KEYWORD: str

    # The keyword used to clear the message queue (e.g., "!CLEARQUEUE").
    CLEARQUEUE_KEYWORD: str

    # The time-to-live (TTL) in seconds for messages in the queue. After this period, the messages are no longer processed.
    MESSAGE_QUEUING_TTL: int

    # If True, the bot activates message queuing to manage messages asynchronously, preventing overload during heavy usage.
    ACTIVATE_MESSAGE_QUEUING: bool

    # New properties for prompt handling.
    # If True, prompts are loaded from the backend, otherwise they are loaded from local paths.
    LOAD_PROMPTS_FROM_BACKEND: bool

    # The local path where core and main prompts are stored if LOAD_PROMPTS_FROM_BACKEND is False.
    LOCAL_PROMPTS_PATH: str

    # The local path where subprompts are stored if LOAD_PROMPTS_FROM_BACKEND is False.
    LOCAL_SUBPROMPTS_PATH: str

    # Specify if the bot uses the user interaction events queue.
    ACTIVATE_USER_INTERACTION_EVENTS_QUEUING: bool
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
    INTERNAL_QUEUE_PROCESSING: Dict[str, Any]

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
