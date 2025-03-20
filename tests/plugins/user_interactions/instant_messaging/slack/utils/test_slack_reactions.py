from plugins.user_interactions.instant_messaging.slack.utils.slack_reactions import (
    SlackReactions,
)
from unittest.mock import AsyncMock, MagicMock

import pytest

@pytest.fixture
def slack_config_reaction():
    return {
        "PROCESSING": "gear",
        "DONE": "white_check_mark",
        "ACKNOWLEDGE": "eyes",
        "GENERATING": "thinking_face",
        "WRITING": "pencil2",
        "ERROR": "redcross",
        "WAIT": "watch",
    }

@pytest.fixture
def slack_reactions(slack_config_reaction):
    return SlackReactions(config=slack_config_reaction)

def test_slack_reactions_constants(slack_reactions):
    assert slack_reactions.reactions["PROCESSING"] == "gear"
    assert slack_reactions.reactions["DONE"] == "white_check_mark"
    assert slack_reactions.reactions["ACKNOWLEDGE"] == "eyes"
    assert slack_reactions.reactions["GENERATING"] == "thinking_face"
    assert slack_reactions.reactions["WRITING"] == "pencil2"
    assert slack_reactions.reactions["ERROR"] == "redcross"
    assert slack_reactions.reactions["WAIT"] == "watch"

# Note: get_reaction cannot be tested without modification because it relies on a non-existent 'value' attribute.
