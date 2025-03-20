from plugins.user_interactions.instant_messaging.slack.utils.slack_reactions import (
    SlackReactions,
)
from unittest.mock import AsyncMock, MagicMock

import pytest

@pytest.fixture
def slack_config_reaction():
    class MockSlackConfig:
        PROCESSING="gear"
        DONE= "white_check_mark"
        ACKNOWLEDGE= "eyes"
        GENERATING= "thinking_face"
        WRITING= "pencil2"
        ERROR= "redcross"
        WAIT= "watch"
    return MockSlackConfig()

@pytest.fixture
def slack_reactions(slack_config_reaction):
    return SlackReactions(config=slack_config_reaction)

def test_slack_reactions_constants(slack_reactions):
    assert slack_reactions.PROCESSING == "gear"
    assert slack_reactions.DONE == "white_check_mark"
    assert slack_reactions.ACKNOWLEDGE == "eyes"
    assert slack_reactions.GENERATING == "thinking_face"
    assert slack_reactions.WRITING == "pencil2"
    assert slack_reactions.ERROR == "redcross"
    assert slack_reactions.WAIT == "watch"

# Note: get_reaction cannot be tested without modification because it relies on a non-existent 'value' attribute.
