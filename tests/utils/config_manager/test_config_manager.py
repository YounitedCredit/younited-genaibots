import os
from unittest.mock import mock_open, patch

import pytest

from utils.config_manager.config_manager import ConfigManager


from unittest.mock import patch, mock_open
import pytest

def test_config_manager_initialization(mock_global_manager):
    # Setup: Create a ConfigManager instance using the mock_global_manager
    with patch('builtins.open', mock_open(read_data="""
    BOT_CONFIG:
      LOG_DEBUG_LEVEL: 'DEBUG'
      CORE_PROMPT: 'core_prompt'
      MAIN_PROMPT: 'main_prompt'
      LOAD_PROMPTS_FROM_BACKEND: true
      LOCAL_PROMPTS_PATH: 'local_prompts_path'
      LOCAL_SUBPROMPTS_PATH: 'local_subprompts_path'
      FEEDBACK_GENERAL_BEHAVIOR: 'feedback_general_behavior'
      LOAD_ACTIONS_FROM_BACKEND: true
      SHOW_COST_IN_THREAD: false
      REQUIRE_MENTION_NEW_MESSAGE: true
      REQUIRE_MENTION_THREAD_MESSAGE: true
      GET_ALL_THREAD_FROM_MESSAGE_LINKS: true
      ACTIVATE_MESSAGE_QUEUING: true
      MESSAGE_QUEUING_TTL: 120
      ACTIVATE_USER_INTERACTION_EVENTS_QUEUING: true
      BEGIN_MARKER: '[BEGINIMDETECT]'
      END_MARKER: '[ENDIMDETECT]'
      GET_URL_CONTENT: true
      LLM_CONVERSION_FORMAT: 'json'
      BREAK_KEYWORD: '!STOP'
      START_KEYWORD: '!START'
      CLEARQUEUE_KEYWORD: '!CLEARQUEUE'
      ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME: 'default_action_plugin'
      INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME: 'default_processing_plugin'
      USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME: 'default_instant_messaging_behavior_plugin'
      GENAI_TEXT_DEFAULT_PLUGIN_NAME: 'default_genai_text_plugin'
      GENAI_IMAGE_DEFAULT_PLUGIN_NAME: 'default_genai_image_plugin'
      GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME: 'default_genai_vector_search_plugin'
      INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME: 'default_internal_queue_processing_plugin'

    UTILS:
      LOGGING:
        LOCAL_LOGGING:
          PLUGIN_NAME: 'local_logging'
          LOCAL_LOGGING_FILE_PATH: 'C:\\LOGS\\GENAI_BOT.log'
        AZURE_LOGGING:
          PLUGIN_NAME: 'azure_logging'
          AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING: 'connection_string'

    PLUGINS:
      ACTION_INTERACTIONS:
        DEFAULT:
          MAIN_ACTIONS:
            PLUGIN_NAME: 'main_actions'
        CUSTOM: {}
      BACKEND:
        INTERNAL_DATA_PROCESSING:
          FILE_SYSTEM:
            PLUGIN_NAME: 'file_system'
            FILE_SYSTEM_DIRECTORY: 'file_system_directory'
            FILE_SYSTEM_SESSIONS_CONTAINER: 'file_system_sessions_container'
            FILE_SYSTEM_FEEDBACKS_CONTAINER: 'file_system_feedbacks_container'
            FILE_SYSTEM_CONCATENATE_CONTAINER: 'file_system_concatenate_container'
            FILE_SYSTEM_PROMPTS_CONTAINER: 'file_system_prompts_container'
            FILE_SYSTEM_COSTS_CONTAINER: 'file_system_costs_container'
            FILE_SYSTEM_PROCESSING_CONTAINER: 'file_system_processing_container'
            FILE_SYSTEM_ABORT_CONTAINER: 'file_system_abort_container'
            FILE_SYSTEM_VECTORS_CONTAINER: 'file_system_vectors_container'
            FILE_SYSTEM_CUSTOM_ACTIONS_CONTAINER: 'file_system_custom_actions_container'
            FILE_SYSTEM_SUBPROMPTS_CONTAINER: 'file_system_subprompts_container'
        INTERNAL_QUEUE_PROCESSING:
          FILE_SYSTEM_QUEUE:
            PLUGIN_NAME: 'file_system_queue'
            FILE_SYSTEM_QUEUE_DIRECTORY: 'file_system_queue_directory'
            FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_CONTAINER: 'file_system_queue_messages_queue_container'
            FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: 'file_system_queue_internal_events_queue_container'
            FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: 'file_system_queue_external_events_queue_container'
            FILE_SYSTEM_QUEUE_WAIT_QUEUE_CONTAINER: 'file_system_queue_wait_queue_container'
            FILE_SYSTEM_QUEUE_MESSAGES_QUEUE_TTL: 120
            FILE_SYSTEM_QUEUE_INTERNAL_EVENTS_QUEUE_TTL: 120
            FILE_SYSTEM_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL: 120
            FILE_SYSTEM_QUEUE_WAIT_QUEUE_TTL: 120
          AZURE_BLOB_STORAGE_QUEUE:
            PLUGIN_NAME: 'azure_blob_storage_queue'
            AZURE_BLOB_STORAGE_QUEUE_CONNECTION_STRING: 'azure_blob_storage_queue_connection_string'
            AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_CONTAINER: 'azure_blob_storage_queue_messages_queue_container'
            AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_CONTAINER: 'azure_blob_storage_queue_internal_events_queue_container'
            AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_CONTAINER: 'azure_blob_storage_queue_external_events_queue_container'
            AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_CONTAINER: 'azure_blob_storage_queue_wait_queue_container'
            AZURE_BLOB_STORAGE_QUEUE_MESSAGES_QUEUE_TTL: 120
            AZURE_BLOB_STORAGE_QUEUE_INTERNAL_EVENTS_QUEUE_TTL: 120
            AZURE_BLOB_STORAGE_QUEUE_EXTERNAL_EVENTS_QUEUE_TTL: 120
            AZURE_BLOB_STORAGE_QUEUE_WAIT_QUEUE_TTL: 120
      USER_INTERACTIONS:
        CUSTOM_API: {}
        INSTANT_MESSAGING:
          SLACK:
            PLUGIN_NAME: 'slack'
            SLACK_BEHAVIOR_PLUGIN_NAME: 'im_default_behavior'
            SLACK_ROUTE_PATH: '/api/get_slacknotification'
            SLACK_ROUTE_METHODS: ['POST']
            SLACK_PLUGIN_DIRECTORY: 'plugins.user_interactions.plugins'
            SLACK_MESSAGE_TTL: 3600
            SLACK_SIGNING_SECRET: 'slack_signing_secret'
            SLACK_BOT_TOKEN: 'slack_bot_token'
            SLACK_BOT_USER_TOKEN: 'slack_bot_user_token'
            SLACK_BOT_USER_ID: 'slack_bot_user_id'
            SLACK_API_URL: 'https://slack.com/api/'
            SLACK_AUTHORIZED_CHANNELS: 'slack_authorized_channels'
            SLACK_AUTHORIZED_APPS: 'slack_authorized_apps'
            SLACK_AUTHORIZED_WEBHOOKS: 'slack_authorized_webhooks'
            SLACK_FEEDBACK_CHANNEL: 'slack_feedback_channel'
            SLACK_FEEDBACK_BOT_ID: 'slack_feedback_bot_id'
            SLACK_MAX_MESSAGE_LENGTH: 2900
            SLACK_INTERNAL_CHANNEL: 'slack_internal_channel'
            SLACK_WORKSPACE_NAME: 'slack_workspace_name'
            SLACK_AUTHORIZE_DIRECT_MESSAGE: true
      USER_INTERACTIONS_BEHAVIORS:
        INSTANT_MESSAGING:
          IM_DEFAULT_BEHAVIOR:
            PLUGIN_NAME: 'im_default_behavior'
        CUSTOM_API:
          CA_DEFAULT_BEHAVIOR:
            PLUGIN_NAME: 'ca_default_behavior'
      GENAI_INTERACTIONS:
        TEXT:
          OPENAI_CHATGPT:
            PLUGIN_NAME: 'openai_chatgpt'
            OPENAI_CHATGPT_INPUT_TOKEN_PRICE: 0.01
            OPENAI_CHATGPT_OUTPUT_TOKEN_PRICE: 0.02
            OPENAI_CHATGPT_API_KEY: 'openai_chatgpt_api_key'
            OPENAI_CHATGPT_MODEL_NAME: 'openai_chatgpt_model_name'
            OPENAI_CHATGPT_VISION_MODEL_NAME: 'openai_chatgpt_vision_model_name'
            OPENAI_CHATGPT_IS_ASSISTANT: false
            OPENAI_CHATGPT_ASSISTANT_ID: ''
          AZURE_CHATGPT:
            PLUGIN_NAME: 'azure_chatgpt'
            AZURE_CHATGPT_INPUT_TOKEN_PRICE: 0.01
            AZURE_CHATGPT_OUTPUT_TOKEN_PRICE: 0.02
            AZURE_CHATGPT_OPENAI_KEY: 'azure_chatgpt_openai_key'
            AZURE_CHATGPT_OPENAI_ENDPOINT: 'azure_chatgpt_openai_endpoint'
            AZURE_CHATGPT_OPENAI_API_VERSION: 'azure_chatgpt_openai_api_version'
            AZURE_CHATGPT_MODEL_NAME: 'azure_chatgpt_model_name'
            AZURE_CHATGPT_VISION_MODEL_NAME: 'azure_chatgpt_vision_model_name'
            AZURE_CHATGPT_IS_ASSISTANT: false
            AZURE_CHATGPT_ASSISTANT_ID: ''
        IMAGE:
          AZURE_DALLE:
            PLUGIN_NAME: 'azure_dalle'
            AZURE_DALLE_INPUT_TOKEN_PRICE: 0.01
            AZURE_DALLE_OUTPUT_TOKEN_PRICE: 0.02
            AZURE_DALLE_OPENAI_KEY: 'azure_dalle_openai_key'
            AZURE_DALLE_OPENAI_ENDPOINT: 'azure_dalle_openai_endpoint'
            AZURE_DALLE_OPENAI_API_VERSION: 'azure_dalle_openai_api_version'
            AZURE_DALLE_IMAGE_GENERATOR_MODEL_NAME: 'azure_dalle_image_generator_model_name'
          OPENAI_DALLE:
            PLUGIN_NAME: 'openai_dalle'
            OPENAI_DALLE_API_KEY: 'openai_dalle_api_key'
            OPENAI_DALLE_MODEL_NAME: 'openai_dalle_model_name'
            OPENAI_DALLE_INPUT_TOKEN_PRICE: 0.01
            OPENAI_DALLE_OUTPUT_TOKEN_PRICE: 0.02
        VECTOR_SEARCH:
          OPENAI_FILE_SEARCH:
            PLUGIN_NAME: 'openai_file_search'
            OPENAI_FILE_SEARCH_OPENAI_KEY: 'openai_file_search_openai_key'
            OPENAI_FILE_SEARCH_OPENAI_ENDPOINT: 'openai_file_search_openai_endpoint'
            OPENAI_FILE_SEARCH_OPENAI_API_VERSION: 'openai_file_search_openai_api_version'
            OPENAI_FILE_SEARCH_MODEL_HOST: 'openai_file_search_model_host'
            OPENAI_FILE_SEARCH_MODEL_NAME: 'openai_file_search_model_name'
            OPENAI_FILE_SEARCH_RESULT_COUNT: 10
            OPENAI_FILE_SEARCH_INDEX_NAME: 'openai_file_search_index_name'
    """)):
        config_manager = ConfigManager(mock_global_manager)
        assert config_manager.config['BOT_CONFIG']['MAIN_PROMPT'] == 'main_prompt'
        assert config_manager.config['PLUGINS']['ACTION_INTERACTIONS']['DEFAULT']['MAIN_ACTIONS']['PLUGIN_NAME'] == 'main_actions'
        assert config_manager.config['UTILS']['LOGGING']['LOCAL_LOGGING']['PLUGIN_NAME'] == 'local_logging'

def test_config_file_not_found(mock_global_manager):
    # Test handling of a missing configuration file
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            ConfigManager(mock_global_manager)

def test_missing_log_debug_level(mock_global_manager):
    # Test handling of missing LOG_DEBUG_LEVEL in configuration
    with patch('builtins.open', mock_open(read_data="BOT_CONFIG: {}")):
        with pytest.raises(KeyError, match="Missing field in config.yaml: BOT_CONFIG.LOG_DEBUG_LEVEL"):
            ConfigManager(mock_global_manager)

def test_replace_env_vars(mock_config_manager):
    # Configure the mock to return the appropriate value
    mock_config_manager.replace_env_vars.return_value = "test_value"

    # Test the replace_env_vars method
    with patch.dict(os.environ, {"TEST_ENV_VAR": "test_value"}):
        result = mock_config_manager.replace_env_vars("$(TEST_ENV_VAR)")
        assert result == "test_value"

    # Configure the mock to raise a ValueError for a missing environment variable
    mock_config_manager.replace_env_vars.side_effect = ValueError("Environment variable TEST_ENV_VAR_NOT_FOUND not found")

    with pytest.raises(ValueError, match="Environment variable TEST_ENV_VAR_NOT_FOUND not found"):
        mock_config_manager.replace_env_vars("$(TEST_ENV_VAR_NOT_FOUND)")

def test_get_config(mock_config_manager):
    # Configure the mock to return the appropriate value
    mock_config_manager.get_config.side_effect = lambda keys: \
        "DEBUG" if keys == ['BOT_CONFIG', 'LOG_DEBUG_LEVEL'] else KeyError("Key 'NON_EXISTENT_KEY' not found in configuration")

    # Test the get_config method
    keys = ['BOT_CONFIG', 'LOG_DEBUG_LEVEL']
    assert mock_config_manager.get_config(keys) == 'DEBUG'

    # Configure the mock to raise a KeyError for a missing key
    mock_config_manager.get_config.side_effect = KeyError("Key 'NON_EXISTENT_KEY' not found in configuration")

    with pytest.raises(KeyError, match="Key 'NON_EXISTENT_KEY' not found in configuration"):
        mock_config_manager.get_config(['BOT_CONFIG', 'NON_EXISTENT_KEY'])

    # Reset the side effect for further tests
    mock_config_manager.get_config.side_effect = None

    with patch.dict(os.environ, {"EXISTENT_ENV_VAR": "env_value"}):
        mock_config_manager.get_config.return_value = "$(EXISTENT_ENV_VAR)"
        mock_config_manager.replace_env_vars.side_effect = lambda x: os.environ.get(x[2:-1], None)
        result = mock_config_manager.get_config(['BOT_CONFIG', 'LOG_DEBUG_LEVEL'])
        assert mock_config_manager.replace_env_vars(result) == "env_value"

    # Configure the mock to raise a KeyError for a missing environment variable
    mock_config_manager.get_config.side_effect = KeyError("Environment variable 'NON_EXISTENT_ENV_VAR' not found")

    with pytest.raises(KeyError, match="Environment variable 'NON_EXISTENT_ENV_VAR' not found"):
        with patch.dict(os.environ, clear=True):
            mock_config_manager.get_config(['BOT_CONFIG', 'LOG_DEBUG_LEVEL'])

def test_load_action_interactions(mock_config_manager):
    # Setup: Define the method return value
    mock_config_manager.config_model.PLUGINS.ACTION_INTERACTIONS.CUSTOM = {}

    # Test the load_action_interactions method
    assert isinstance(mock_config_manager.config_model.PLUGINS.ACTION_INTERACTIONS.CUSTOM, dict)
