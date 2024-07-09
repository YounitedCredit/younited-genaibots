
import pytest

from core.plugin_base import PluginBase


def test_plugin_base_initialization(mock_global_manager):
    class ConcretePlugin(PluginBase):
        def initialize(self):
            pass

        @property
        def plugin_name(self):
            return self._plugin_name

        @plugin_name.setter
        def plugin_name(self, value):
            self._plugin_name = value

    # Test successful initialization
    plugin = ConcretePlugin(mock_global_manager)
    assert plugin.global_manager == mock_global_manager
    assert plugin.plugin_name == "ConcretePlugin"

    # Test initialization with incorrect global_manager type
    with pytest.raises(TypeError):
        ConcretePlugin("not_a_global_manager")

def test_plugin_base_methods_and_properties(mock_global_manager):
    class ConcretePlugin(PluginBase):
        def initialize(self):
            pass

        @property
        def plugin_name(self):
            return self._plugin_name

        @plugin_name.setter
        def plugin_name(self, value):
            self._plugin_name = value

    plugin = ConcretePlugin(mock_global_manager)

    # Test setting and getting plugin_name
    plugin.plugin_name = "TestPlugin"
    assert plugin.plugin_name == "TestPlugin"

    # Ensure NotImplementedError is raised for abstract methods if not overridden
    class IncompletePlugin(PluginBase):
        pass

    with pytest.raises(TypeError):
        IncompletePlugin(mock_global_manager)

@pytest.mark.usefixtures("mock_global_manager")
class TestPluginBase:
    def test_initialization(self, mock_global_manager):
        class ConcretePlugin(PluginBase):
            def initialize(self):
                pass

            @property
            def plugin_name(self):
                return self._plugin_name

            @plugin_name.setter
            def plugin_name(self, value):
                self._plugin_name = value

        # Test successful initialization
        plugin = ConcretePlugin(mock_global_manager)
        assert plugin.global_manager == mock_global_manager
        assert plugin.plugin_name == "ConcretePlugin"

        # Test initialization with incorrect global_manager type
        with pytest.raises(TypeError):
            ConcretePlugin("not_a_global_manager")

    def test_methods_and_properties(self, mock_global_manager):
        class ConcretePlugin(PluginBase):
            def initialize(self):
                pass

            @property
            def plugin_name(self):
                return self._plugin_name

            @plugin_name.setter
            def plugin_name(self, value):
                self._plugin_name = value

        plugin = ConcretePlugin(mock_global_manager)

        # Test setting and getting plugin_name
        plugin.plugin_name = "TestPlugin"
        assert plugin.plugin_name == "TestPlugin"

        # Ensure NotImplementedError is raised for abstract methods if not overridden
        class IncompletePlugin(PluginBase):
            pass

        with pytest.raises(TypeError):
            IncompletePlugin(mock_global_manager)
