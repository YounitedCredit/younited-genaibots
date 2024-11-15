from core.user_interactions.reaction_base import ReactionBase


class GenericRestReactions(ReactionBase):
    PROCESSING = "processing"
    DONE = "done"
    ACKNOWLEDGE = "acknowledge"
    GENERATING = "generating"
    WRITING = "writing"
    ERROR = "error"
    WAIT = "wait"

    def get_reaction(self):
        return self.value
