from core.user_interactions.reaction_base import ReactionBase


class TeamsReactions(ReactionBase):
    PROCESSING = "\U00002699"  # Gear
    DONE = "\U00002705"  # White Check Mark
    ACKNOWLEDGE = "\U0001F440"  # Eyes
    GENERATING = "\U0001F914"  # Thinking Face
    WRITING = "\U0000270F"  # Pencil
    ERROR = "\U0000274C"  # Cross Mark
    WAIT = "\U000023F1"  # Stopwatch

    def get_reaction(self):
        return self.value
