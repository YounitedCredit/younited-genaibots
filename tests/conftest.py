import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.storage.blob import BlobServiceClient

from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.reaction_base import ReactionBase
from core.user_interactions_behaviors.user_interactions_behavior_dispatcher import (
    UserInteractionsBehaviorsDispatcher,
)
from core.user_interactions_behaviors.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
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

# Utiliser la boucle SelectorEventLoop sur Windows
if sys.platform == "win32":
    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.SelectorEventLoop()
        yield loop
        loop.close()
else:
    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

@pytest.fixture
def mock_app():
    return MagicMock()

@pytest.fixture
def mock_utils():
    return Utils(
        LOGGING=Logging(
            LOCAL_LOGGING=LocalLogging(
                PLUGIN_NAME="local_logging",
                LEVEL="DEBUG",
                LOCAL_LOGGING_FILE_PATH="log.txt"  # Ajoutez ce champ requis
            ),
            AZURE_LOGGING=AzureLogging(
                PLUGIN_NAME="azure_logging",
                AZURE_LOGGING_APPLICATIONINSIGHTS_CONNECTION_STRING="connection_string"
            )
        )
    )

@pytest.fixture
def mock_plugins():
    return Plugins(
        ACTION_INTERACTIONS=ActionInteractions(
            DEFAULT={"default_action_interaction": Plugin(PLUGIN_NAME="plugin name")},
            CUSTOM={"custom_action_interaction": Plugin(PLUGIN_NAME="plugin name")}
        ),
        BACKEND=Backend(
            INTERNAL_DATA_PROCESSING={"some key": "some value"}
        ),
        USER_INTERACTIONS=UserInteractions(
            INSTANT_MESSAGING={"some key": "some value"},
            CUSTOM_API={"custom_api": "some_custom_api"}
        ),
        GENAI_INTERACTIONS=GenaiInteractions(
            TEXT={"some key": "some value"},
            IMAGE={"some key": "some value"},
            VECTOR_SEARCH={"some key": "some value"}
        ),
        USER_INTERACTIONS_BEHAVIORS=UserInteractionsBehaviors(
            INSTANT_MESSAGING={"some key": "some value"},
            CUSTOM_API={"some key": "some value"}
        )
    )

@pytest.fixture
def mock_config_manager(mock_utils, mock_plugins):
    mock = MagicMock()
    mock.config = ConfigModel(
        BOT_CONFIG=BotConfig(
            CORE_PROMPT="core_prompt",
            MAIN_PROMPT="main_prompt",
            PROMPTS_FOLDER="prompt_folder",
            SUBPROMPTS_FOLDER="subprompt_folder",
            FEEDBACK_GENERAL_BEHAVIOR="feedback_general_behavior",
            REQUIRE_MENTION_NEW_MESSAGE=True,
            REQUIRE_MENTION_THREAD_MESSAGE=True,
            GET_ALL_THREAD_FROM_MESSAGE_LINKS=True,
            LOG_DEBUG_LEVEL="DEBUG",
            SHOW_COST_IN_THREAD=True,
            ACKNOWLEDGE_NONPROCESSED_MESSAGE=True,
            GET_URL_CONTENT=True,
            ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME="action_interactions_default_plugin_name",
            INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME="internal_data_processing_default_plugin_name",
            USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME="user_interactions_instant_messaging_behavior_default_plugin_name",
            GENAI_TEXT_DEFAULT_PLUGIN_NAME="genai_text_default_plugin_name",
            GENAI_IMAGE_DEFAULT_PLUGIN_NAME="genai_image_default_plugin_name",
            USER_INTERACTIONS_INSTANT_MESSAGING_DEFAULT_PLUGIN_NAME="test_plugin",
            GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME="genai_vector_search_default_plugin_name",
            LLM_CONVERSION_FORMAT="LLM_conversion_format",
            BREAK_KEYWORD="start",
            START_KEYWORD="stop",
            LOAD_ACTIONS_FROM_BACKEND = False,
            RECORD_NONPROCESSED_MESSAGES=False
        ),
        UTILS=mock_utils,
        PLUGINS=mock_plugins,
    )
    return mock

@pytest.fixture
def mock_plugin_manager():
    return MagicMock()

@pytest.fixture
def mock_user_interactions_handler():
    return MagicMock()

@pytest.fixture
def mock_action_interactions_handler():
    return MagicMock()

@pytest.fixture
def mock_prompt_manager():
    return MagicMock()

def mock_from_connection_string(*args, **kwargs):
    return MagicMock(spec=BlobServiceClient)

@pytest.fixture
def mock_global_manager(mock_config_manager, mock_plugin_manager, mock_user_interactions_handler,
                        mock_action_interactions_handler, mock_prompt_manager):
    mock_global_manager = MagicMock(spec=GlobalManager)
    mock_global_manager.config_manager = mock_config_manager
    mock_global_manager.bot_config = mock_config_manager.config.BOT_CONFIG
    mock_global_manager.plugin_manager = mock_plugin_manager
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.user_interactions_behavior_dispatcher = AsyncMock()
    mock_global_manager.genai_vectorsearch_dispatcher = AsyncMock()
    mock_global_manager.action_interactions_handler = mock_action_interactions_handler
    mock_global_manager.prompt_manager = mock_prompt_manager
    mock_global_manager.base_directory = Path('')
    mock_global_manager.available_actions = {}
    mock_global_manager.logger = MagicMock()
    mock_global_manager.genai_image_generator_dispatcher = AsyncMock()
    return mock_global_manager

@pytest.fixture
def mock_user_interactions_plugin():
    plugin = MagicMock(spec=UserInteractionsPluginBase)
    plugin.plugin_name = "test_plugin"
    plugin.send_message = AsyncMock()
    plugin.upload_file = AsyncMock()
    plugin.add_reaction = AsyncMock()
    plugin.remove_reaction = AsyncMock()
    plugin.request_to_notification_data = AsyncMock()
    plugin.process_event_data = AsyncMock()
    return plugin

@pytest.fixture
def mock_user_interactions_behaviors_dispatcher(mock_global_manager):
    dispatcher = UserInteractionsBehaviorsDispatcher(global_manager=mock_global_manager)
    dispatcher.plugins = {"default_category": [MagicMock(spec=UserInteractionsPluginBase, plugin_name="test_plugin")]}
    return dispatcher

@pytest.fixture
def mock_user_interactions_dispatcher(mock_global_manager, mock_plugins):
    dispatcher = UserInteractionsDispatcher(global_manager=mock_global_manager)
    dispatcher.plugins = {"default_category": [MagicMock(spec=UserInteractionsPluginBase, plugin_name="test_plugin")]}
    dispatcher.initialize(dispatcher.plugins["default_category"])
    return dispatcher

@pytest.fixture
def mock_reaction_base():
    reaction_base = MagicMock(spec=ReactionBase)
    reaction_base.ACKNOWLEDGE = "ACKNOWLEDGE"
    reaction_base.DONE = "DONE"
    reaction_base.ERROR = "ERROR"
    reaction_base.GENERATING = "GENERATING"
    reaction_base.PROCESSING = "PROCESSING"
    reaction_base.WAIT = "WAIT"
    reaction_base.WRITING = "WRITING"
    reaction_base.get_reaction = MagicMock(return_value="Some reaction")
    return reaction_base

@pytest.fixture
def mock_incoming_notification_data_base():
    event_data = MagicMock(
        spec=IncomingNotificationDataBase,
        timestamp="timestamp",
        event_label="event_label",
        channel_id="channel_id",
        thread_id="thread_id",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        user_id="user_id",
        is_mention=True,
        text="text",
        origin_plugin_name="plugin_name"  # Adding the mandatory field
    )
    return event_data