import pytest
from pydantic import ValidationError

from utils.config_manager.config_model import (
    ActionInteractions,
    AzureLogging,
    Backend,
    BotConfig,
    ConfigModel,
    GenaiInteractions,
    LocalLogging,
    Logging,
    Plugin,
    Plugins,
    UserInteractions,
    UserInteractionsBehaviors,
    Utils,
)

def test_bot_config():
    # Test valid BotConfig
    valid_data = {
        "CORE_PROMPT": "core_prompt",
        "MAIN_PROMPT": "main_prompt",
        "PROMPTS_FOLDER": "prompts_folder",
        "SUBPROMPTS_FOLDER": "subprompts_folder",
        "FEEDBACK_GENERAL_BEHAVIOR": "feedback_behavior",
        "REQUIRE_MENTION_NEW_MESSAGE": True,
        "REQUIRE_MENTION_THREAD_MESSAGE": True,
        "LOG_DEBUG_LEVEL": "DEBUG",
        "SHOW_COST_IN_THREAD": True,
        "GET_URL_CONTENT": True,
        "ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME": "default_action_plugin",
        "INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME": "default_processing_plugin",
        "USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME": "default_instant_messaging_plugin",
        "GENAI_TEXT_DEFAULT_PLUGIN_NAME": "default_genai_text_plugin",
        "GENAI_IMAGE_DEFAULT_PLUGIN_NAME": "default_genai_image_plugin",
        "GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME": "default_genai_vector_search_plugin",
        "LLM_CONVERSION_FORMAT": "conversion_format",
        "BREAK_KEYWORD": "break",
        "START_KEYWORD": "start",
        "CLEARQUEUE_KEYWORD": "clearqueue",
        "LOAD_ACTIONS_FROM_BACKEND": True,
        "GET_ALL_THREAD_FROM_MESSAGE_LINKS": False,
        "ACTIVATE_MESSAGE_QUEUING": False,
        "MESSAGE_QUEUING_TTL": 120,
        "INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME": "default_queue_plugin",
        "LOAD_PROMPTS_FROM_BACKEND": True,
        "LOCAL_PROMPTS_PATH": "local_prompts_path",
        "LOCAL_SUBPROMPTS_PATH": "local_subprompts_path",
        "ACTIVATE_USER_INTERACTION_EVENTS_QUEUING": True
    }
    bot_config = BotConfig(**valid_data)
    assert bot_config.CORE_PROMPT == "core_prompt"

    # Test invalid BotConfig (missing required field)
    invalid_data = valid_data.copy()
    invalid_data.pop("CORE_PROMPT")
    with pytest.raises(ValidationError):
        BotConfig(**invalid_data)

def test_logging():
    # Test valid Logging
    file_data = {"PLUGIN_NAME": "file_plugin", "LOCAL_LOGGING_FILE_PATH": "path/to/log"}
    azure_data = {"PLUGIN_NAME": "azure_plugin", "AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING": "connection_string"}

    # Ensure LOCAL_LOGGING and AZURE_LOGGING are properly set
    logging = Logging(LOCAL_LOGGING=LocalLogging(**file_data), AZURE_LOGGING=AzureLogging(**azure_data))

    assert logging.LOCAL_LOGGING.PLUGIN_NAME == "file_plugin"
    assert logging.LOCAL_LOGGING.LOCAL_LOGGING_FILE_PATH == "path/to/log"
    assert logging.AZURE_LOGGING.PLUGIN_NAME == "azure_plugin"

    # Test invalid Logging (invalid nested model)
    invalid_file_data = file_data.copy()
    invalid_file_data["LOCAL_LOGGING_FILE_PATH"] = 123  # Invalid type for LOCAL_LOGGING_FILE_PATH
    with pytest.raises(ValidationError):
        Logging(LOCAL_LOGGING=LocalLogging(**invalid_file_data))

def test_utils():
    # Test valid Utils
    file_data = {"PLUGIN_NAME": "file_plugin", "LOCAL_LOGGING_FILE_PATH": "path/to/log"}

    # Ensure LOCAL_LOGGING is properly set in Logging
    logging = Logging(LOCAL_LOGGING=LocalLogging(**file_data))
    utils = Utils(LOGGING=logging)

    assert utils.LOGGING.LOCAL_LOGGING.LOCAL_LOGGING_FILE_PATH == "path/to/log"

def test_plugins():
    # Test valid Plugins
    plugin_data = {"PLUGIN_NAME": "plugin_name"}
    action_interactions = ActionInteractions(DEFAULT={"default_plugin": Plugin(**plugin_data)})
    backend = Backend(
        INTERNAL_DATA_PROCESSING={"key": "value"},
        INTERNAL_QUEUE_PROCESSING={"key": "value"}
    )
    user_interactions = UserInteractions(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})
    genai_interactions = GenaiInteractions(TEXT={"key": "value"}, IMAGE={"key": "value"}, VECTOR_SEARCH={"key": "value"})
    user_interactions_behaviors = UserInteractionsBehaviors(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})

    plugins = Plugins(
        ACTION_INTERACTIONS=action_interactions,
        BACKEND=backend,
        USER_INTERACTIONS=user_interactions,
        GENAI_INTERACTIONS=genai_interactions,
        USER_INTERACTIONS_BEHAVIORS=user_interactions_behaviors
    )

    assert plugins.ACTION_INTERACTIONS.DEFAULT["default_plugin"].PLUGIN_NAME == "plugin_name"

def test_config_model():
    # Test valid ConfigModel
    bot_config_data = {
        "CORE_PROMPT": "core_prompt",
        "MAIN_PROMPT": "main_prompt",
        "PROMPTS_FOLDER": "prompts_folder",
        "SUBPROMPTS_FOLDER": "subprompts_folder",
        "FEEDBACK_GENERAL_BEHAVIOR": "feedback_behavior",
        "REQUIRE_MENTION_NEW_MESSAGE": True,
        "REQUIRE_MENTION_THREAD_MESSAGE": True,
        "LOG_DEBUG_LEVEL": "DEBUG",
        "SHOW_COST_IN_THREAD": True,
        "GET_URL_CONTENT": True,
        "ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME": "default_action_plugin",
        "INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME": "default_processing_plugin",
        "USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME": "default_instant_messaging_plugin",
        "GENAI_TEXT_DEFAULT_PLUGIN_NAME": "default_genai_text_plugin",
        "GENAI_IMAGE_DEFAULT_PLUGIN_NAME": "default_genai_image_plugin",
        "GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME": "default_genai_vector_search_plugin",
        "LLM_CONVERSION_FORMAT": "conversion_format",
        "BREAK_KEYWORD": "break",
        "START_KEYWORD": "start",
        "CLEARQUEUE_KEYWORD": '!CLEARQUEUE',
        "LOAD_ACTIONS_FROM_BACKEND": False,
        "GET_ALL_THREAD_FROM_MESSAGE_LINKS": True,
        "MESSAGE_QUEUING_TTL": 120,
        "ACTIVATE_MESSAGE_QUEUING": True,
        "INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME": "default_queue_plugin",
        "LOAD_PROMPTS_FROM_BACKEND": True,
        "LOCAL_PROMPTS_PATH": "local_prompts_path",
        "LOCAL_SUBPROMPTS_PATH": "local_subprompts_path",
        "ACTIVATE_USER_INTERACTION_EVENTS_QUEUING": True
    }
    file_data = {"PLUGIN_NAME": "file_plugin", "LOCAL_LOGGING_FILE_PATH": "path/to/log"}

    # Ensure LOCAL_LOGGING is properly set
    logging = Logging(LOCAL_LOGGING=LocalLogging(**file_data))
    utils = Utils(LOGGING=logging)

    plugin_data = {"PLUGIN_NAME": "plugin_name"}
    action_interactions = ActionInteractions(DEFAULT={"default_plugin": Plugin(**plugin_data)})
    backend = Backend(
        INTERNAL_DATA_PROCESSING={"key": "value"},
        INTERNAL_QUEUE_PROCESSING={"key": "value"}
    )
    user_interactions = UserInteractions(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})
    genai_interactions = GenaiInteractions(TEXT={"key": "value"}, IMAGE={"key": "value"}, VECTOR_SEARCH={"key": "value"})
    user_interactions_behaviors = UserInteractionsBehaviors(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})

    plugins = Plugins(
        ACTION_INTERACTIONS=action_interactions,
        BACKEND=backend,
        USER_INTERACTIONS=user_interactions,
        GENAI_INTERACTIONS=genai_interactions,
        USER_INTERACTIONS_BEHAVIORS=user_interactions_behaviors
    )

    config_model = ConfigModel(BOT_CONFIG=BotConfig(**bot_config_data), UTILS=utils, PLUGINS=plugins)

    assert config_model.BOT_CONFIG.CORE_PROMPT == "core_prompt"
    assert config_model.UTILS.LOGGING.LOCAL_LOGGING.PLUGIN_NAME == "file_plugin"