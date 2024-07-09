from abc import ABC, abstractmethod


class PluginBase(ABC):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        if not isinstance(global_manager, GlobalManager):
            raise TypeError("global_manager must be an instance of GlobalManager")
        self.global_manager = global_manager
        self.plugin_name = self.__class__.__name__

    @abstractmethod
    def initialize(self):
        """Initialize the plugin"""
        raise NotImplementedError("This method should be overridden by subclasses")

    @property
    @abstractmethod
    def plugin_name(self):
        """
        Property for the route path.
        """
        raise NotImplementedError("This method should be overridden by subclasses")

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

