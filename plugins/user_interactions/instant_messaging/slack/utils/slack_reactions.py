
from core.user_interactions.reaction_base import ReactionBase


class SlackReactions(ReactionBase):
    PROCESSING = "gear"
    DONE = "white_check_mark"
    ACKNOWLEDGE = "eyes"
    GENERATING = "thinking_face"
    WRITING = "pencil2"
    ERROR = "redcross"
    WAIT = "watch"

    def get_reaction(self):
        return self.value
