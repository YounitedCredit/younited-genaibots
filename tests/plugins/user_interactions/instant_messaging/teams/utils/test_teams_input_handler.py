
import pytest

from plugins.user_interactions.instant_messaging.teams.teams import TeamsConfig
from plugins.user_interactions.instant_messaging.teams.utils.teams_input_handler import (
    TeamsInputHandler,
)


@pytest.fixture
def teams_config():
    config = TeamsConfig(
        PLUGIN_NAME="teams",
        TEAMS_APP_ID="app_id",
        TEAMS_APP_PASSWORD="app_password",
        ROUTE_PATH="/api/messages",
        ROUTE_METHODS=["POST"],
        TEAMS_BOT_USER_ID="bot_user_id",
        TEAMS_AUTHORIZED_CHANNELS="authorized_channel_1,authorized_channel_2",
        TEAMS_FEEDBACK_CHANNEL="feedback_channel",
        TEAMS_FEEDBACK_BOT_USER_ID="feedback_bot_user_id",
        BEHAVIOR_PLUGIN_NAME="behavior_plugin"
    )
    return config

def test_teams_input_handler_initialization(mock_global_manager, teams_config):
    handler = TeamsInputHandler(mock_global_manager, teams_config)

    assert handler.global_manager == mock_global_manager
    assert handler.logger == mock_global_manager.logger
    assert handler.plugin_manager == mock_global_manager.plugin_manager
    assert handler.teams_config == teams_config

    # Mock the conversion to set for testing
    handler.TEAMS_AUTHORIZED_CHANNELS = set(teams_config.TEAMS_AUTHORIZED_CHANNELS.split(","))
    expected_channels = set(["authorized_channel_1", "authorized_channel_2"])
    assert handler.TEAMS_AUTHORIZED_CHANNELS == expected_channels
    assert handler.TEAMS_BOT_USER_ID == "bot_user_id"

def test_teams_input_handler_no_config(mock_global_manager):
    handler = TeamsInputHandler(mock_global_manager, None)
    mock_global_manager.logger.error.assert_called_once_with("No 'TEAMS' configuration found in 'USER_INTERACTIONS_PLUGINS'")
