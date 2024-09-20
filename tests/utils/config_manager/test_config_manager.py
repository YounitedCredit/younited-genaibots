import os
from unittest.mock import mock_open, patch

import pytest

from utils.config_manager.config_manager import ConfigManager

def test_config_manager_initialization(mock_global_manager):
    # Setup: Create a ConfigManager instance using the mock_global_manager
    with patch('builtins.open', mock_open(read_data="""
    BOT_CONFIG:
      CORE_PROMPT: 'core_prompt'
      MAIN_PROMPT: 'main_prompt'
      PROMPTS_FOLDER: 'prompt_folder'
      SUBPROMPTS_FOLDER: 'subprompt_folder'
      FEEDBACK_GENERAL_BEHAVIOR: 'feedback_general_behavior'
      REQUIRE_MENTION_NEW_MESSAGE: true
      REQUIRE_MENTION_THREAD_MESSAGE: true
      LOG_DEBUG_LEVEL: 'DEBUG'
      SHOW_COST_IN_THREAD: true
      ACKNOWLEDGE_NONPROCESSED_MESSAGE: true
      GET_ALL_THREAD_FROM_MESSAGE_LINKS: true
      GET_URL_CONTENT: true
      ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME: 'default_action_plugin'
      INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME: 'default_processing_plugin'
      USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME: 'default_instant_messaging_behavior_plugin'
      GENAI_TEXT_DEFAULT_PLUGIN_NAME: 'default_genai_text_plugin'
      GENAI_IMAGE_DEFAULT_PLUGIN_NAME: 'default_genai_image_plugin'
      GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME: 'default_genai_vector_search_plugin'
      LLM_CONVERSION_FORMAT: 'LLM_conversion_format'
      BREAK_KEYWORD: 'start'
      START_KEYWORD: 'stop'
      LOAD_ACTIONS_FROM_BACKEND: False
    PLUGINS:
      ACTION_INTERACTIONS:
        CUSTOM: {}
        DEFAULT: {}
      BACKEND:
        INTERNAL_DATA_PROCESSING: {}
      USER_INTERACTIONS:
        INSTANT_MESSAGING: {}
        CUSTOM_API: {}
      GENAI_INTERACTIONS:
        TEXT: {}
        IMAGE: {}
        VECTOR_SEARCH: {}
      USER_INTERACTIONS_BEHAVIORS:
        INSTANT_MESSAGING: {}
        CUSTOM_API: {}
    UTILS:
      LOGGING:
        FILE:
          PLUGIN_NAME: 'file_logging'
          LEVEL: 'DEBUG'
          FILE_PATH: 'log.txt'
        AZURE:
          PLUGIN_NAME: 'azure_logging'
          APPLICATIONINSIGHTS_CONNECTION_STRING: 'connection_string'
    """)):
        config_manager = ConfigManager(mock_global_manager)
        assert config_manager.config['BOT_CONFIG']['MAIN_PROMPT'] == 'main_prompt'
        assert config_manager.config['PLUGINS']['ACTION_INTERACTIONS'] == {'CUSTOM': {}, 'DEFAULT': {}}
        assert config_manager.config['UTILS']['LOGGING']['FILE']['PLUGIN_NAME'] == 'file_logging'

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
