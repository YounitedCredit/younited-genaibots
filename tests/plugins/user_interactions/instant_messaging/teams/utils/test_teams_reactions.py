from plugins.user_interactions.instant_messaging.teams.utils.teams_reactions import (
    TeamsReactions,
)


def test_teams_reactions_definitions():
    assert TeamsReactions.PROCESSING == "\U00002699"  # Gear
    assert TeamsReactions.DONE == "\U00002705"  # White Check Mark
    assert TeamsReactions.ACKNOWLEDGE == "\U0001F440"  # Eyes
    assert TeamsReactions.GENERATING == "\U0001F914"  # Thinking Face
    assert TeamsReactions.WRITING == "\U0000270F"  # Pencil
    assert TeamsReactions.ERROR == "\U0000274C"  # Cross Mark
    assert TeamsReactions.WAIT == "\U000023F1"  # Stopwatch

def test_get_reaction():
    class MockReaction(TeamsReactions):
        def __init__(self, value):
            self.value = value

    mock_reaction = MockReaction(TeamsReactions.PROCESSING)
    assert mock_reaction.get_reaction() == TeamsReactions.PROCESSING

    mock_reaction.value = TeamsReactions.DONE
    assert mock_reaction.get_reaction() == TeamsReactions.DONE

    mock_reaction.value = TeamsReactions.ACKNOWLEDGE
    assert mock_reaction.get_reaction() == TeamsReactions.ACKNOWLEDGE

    mock_reaction.value = TeamsReactions.GENERATING
    assert mock_reaction.get_reaction() == TeamsReactions.GENERATING

    mock_reaction.value = TeamsReactions.WRITING
    assert mock_reaction.get_reaction() == TeamsReactions.WRITING

    mock_reaction.value = TeamsReactions.ERROR
    assert mock_reaction.get_reaction() == TeamsReactions.ERROR

    mock_reaction.value = TeamsReactions.WAIT
    assert mock_reaction.get_reaction() == TeamsReactions.WAIT
