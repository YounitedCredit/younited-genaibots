from plugins.user_interactions.instant_messaging.slack.utils.slack_reactions import (
    SlackReactions,
)


def test_slack_reactions_constants():
    reactions = SlackReactions()
    assert reactions.PROCESSING == "gear"
    assert reactions.DONE == "white_check_mark"
    assert reactions.ACKNOWLEDGE == "eyes"
    assert reactions.GENERATING == "thinking_face"
    assert reactions.WRITING == "pencil2"
    assert reactions.ERROR == "redcross"
    assert reactions.WAIT == "watch"

# Note: get_reaction cannot be tested without modification because it relies on a non-existent 'value' attribute.
