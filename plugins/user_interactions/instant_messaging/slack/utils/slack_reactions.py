from core.user_interactions.reaction_base import ReactionBase


class SlackReactions(ReactionBase):
    DEFAULT_REACTIONS = {
        "PROCESSING": "gear",
        "DONE": "white_check_mark",
        "ACKNOWLEDGE": "eyes",
        "GENERATING": "thinking_face",
        "WRITING": "pencil2",
        "ERROR": "redcross",
        "WAIT": "watch",
    }

    def __init__(self, config=None):
        self.reactions = config or self.DEFAULT_REACTIONS

    def __getattr__(self, name):
        if name in self.reactions:
            return self.reactions[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def get_reaction(self):
        return self.value
