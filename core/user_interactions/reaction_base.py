from abc import ABC, abstractmethod


class ReactionBase(ABC):
    """
    Abstract base class for reactions.
    """

    @property
    def ACKNOWLEDGE(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    def PROCESSING(self):
        """
        Property for the processing reaction.
        """
        raise NotImplementedError

    @property
    def DONE(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    def GENERATING(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    def WRITING(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    def ERROR(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    def WAIT(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    def get_reaction(self):
        """
        Get the reaction.
        """
        raise NotImplementedError
