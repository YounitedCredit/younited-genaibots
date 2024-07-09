# tests/core/backend/test_internal_data_plugin_base.py

from abc import ABC

from core.backend.internal_data_processing_base import InternalDataPluginBase
from core.plugin_base import PluginBase


# Concrete class for testing
class ConcreteInternalDataPlugin(InternalDataPluginBase):
    def initialize(self):
        pass

    @property
    def plugin_name(self):
        return "concrete_internal_data_plugin"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

def test_internal_data_plugin_base_instantiation(mock_global_manager):
    # Instantiate the concrete plugin with the mock global manager
    plugin = ConcreteInternalDataPlugin(mock_global_manager)
    # Check if the plugin is an instance of InternalDataPluginBase
    assert isinstance(plugin, InternalDataPluginBase)

def test_internal_data_plugin_base_inheritance(mock_global_manager):
    # Instantiate the concrete plugin with the mock global manager
    plugin = ConcreteInternalDataPlugin(mock_global_manager)
    # Check if the plugin is an instance of PluginBase and ABC
    assert isinstance(plugin, PluginBase)
    assert isinstance(plugin, ABC)
