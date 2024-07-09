from abc import ABC, abstractmethod


class ReactionBase(ABC):
    """
    Abstract base class for reactions.
    """

    @property
    @abstractmethod
    def ACKNOWLEDGE(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def PROCESSING(self):
        """
        Property for the processing reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def DONE(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def GENERATING(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def WRITING(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def ERROR(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def WAIT(self):
        """
        Property for the done reaction.
        """
        raise NotImplementedError

    @abstractmethod
    def get_reaction(self):
        """
        Get the reaction.
        """
        raise NotImplementedError
