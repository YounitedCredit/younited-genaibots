from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_base import PluginBase
from utils.config_manager.config_model import Plugins
from utils.plugin_manager.plugin_manager import PluginManager


@pytest.fixture
def plugin_manager(mock_global_manager, mock_plugins):
    mock_global_manager.config_manager.config_model.PLUGINS = mock_plugins
    return PluginManager(base_directory='plugins', global_manager=mock_global_manager)

def test_init_plugin_manager(mock_global_manager, mock_plugins):
    with pytest.raises(TypeError):
        PluginManager(base_directory='plugins', global_manager=MagicMock())

    mock_global_manager.config_manager.config_model.PLUGINS = mock_plugins
    pm = PluginManager(base_directory='plugins', global_manager=mock_global_manager)
    assert pm.base_directory == 'plugins'
    assert pm.config_manager == mock_global_manager.config_manager
    assert isinstance(pm.plugin_configs, Plugins)
    assert pm.global_manager == mock_global_manager
    assert pm.logger == mock_global_manager.logger
    assert pm.plugins == {}

def test_load_plugin(plugin_manager):
    with patch('utils.plugin_manager.plugin_manager.importlib.import_module') as mock_import_module:
        mock_mod = MagicMock()
        mock_import_module.return_value = mock_mod

        # Simulate the MainActionsPlugin class, as expected by load_plugin
        class MainActionsPlugin(PluginBase):
            def __init__(self, global_manager):
                super().__init__(global_manager)
                self._plugin_name = "main_actions"

            def initialize(self):
                pass

            @property
            def plugin_name(self):
                return self._plugin_name

        # Add the MainActionsPlugin class to the mocked module
        mock_mod.MainActionsPlugin = MainActionsPlugin

        # Use the module name used by load_plugin, following the expected format
        module_name = 'plugins.action_interactions.default.main_actions.main_actions'

        # Patch PluginBase and call load_plugin
        with patch('core.plugin_base.PluginBase', new=MagicMock()):
            plugin_instance = plugin_manager.load_plugin('plugins', module_name)

            # Check that the plugin was correctly loaded
            assert plugin_instance is not None, "The plugin was not loaded correctly"
            assert isinstance(plugin_instance, MainActionsPlugin)


@pytest.mark.asyncio
async def test_load_custom_actions_from_backend(plugin_manager):
    mock_dispatcher = AsyncMock()
    plugin_manager.global_manager.backend_internal_data_processing_dispatcher = mock_dispatcher

    # Configuration du mock pour retourner des fichiers d'actions
    mock_dispatcher.list_container_files.return_value = ['action1', 'action2']
    mock_dispatcher.read_data_content.return_value = 'class Action1(ActionBase): pass'

    with patch('core.action_interactions.action_base.ActionBase', new=MagicMock()):
        await plugin_manager._load_custom_actions_from_backend([])

    mock_dispatcher.list_container_files.assert_called_once_with('custom_actions')
    mock_dispatcher.read_data_content.assert_called()


def test_get_plugin_by_category(plugin_manager):
    plugin_manager.plugins = {'CATEGORY': {'SUBCATEGORY': 'plugin_instance'}}
    assert plugin_manager.get_plugin_by_category('CATEGORY', 'SUBCATEGORY') == 'plugin_instance'
    assert plugin_manager.get_plugin_by_category('CATEGORY') == {'SUBCATEGORY': 'plugin_instance'}
    assert plugin_manager.get_plugin_by_category('NON_EXISTENT') is None

def test_get_plugin(plugin_manager):
    with patch.object(plugin_manager, 'load_plugin', return_value='plugin_instance') as mock_load_plugin:
        plugin = plugin_manager.get_plugin(plugin_name='plugin_name', subdirectory='category.subdirectory')
        mock_load_plugin.assert_called_once_with('plugins', 'category.subdirectory.plugin_name.plugin_name')
        assert plugin == 'plugin_instance'
        assert 'CATEGORY' in plugin_manager.plugins
        assert 'SUBDIRECTORY' in plugin_manager.plugins['CATEGORY']
        assert plugin_manager.plugins['CATEGORY']['SUBDIRECTORY'] == ['plugin_instance']

    # Test with plugin loading failure
    with patch.object(plugin_manager, 'load_plugin', side_effect=Exception("Failed to load plugin")) as mock_load_plugin:
        plugin = plugin_manager.get_plugin(plugin_name='plugin_name', subdirectory='category.subdirectory')
        assert plugin is None

def test_load_plugin(plugin_manager):
    with patch('utils.plugin_manager.plugin_manager.importlib.import_module') as mock_import_module:
        mock_mod = MagicMock()
        mock_import_module.return_value = mock_mod

        # Correct implementation of the MainActionsPlugin class, with proper getter and setter for plugin_name
        class MainActionsPlugin(PluginBase):
            def __init__(self, global_manager):
                super().__init__(global_manager)
                self._plugin_name = "main_actions"

            def initialize(self):
                pass

            # Getter for plugin_name
            @property
            def plugin_name(self):
                return self._plugin_name

            # Setter for plugin_name
            @plugin_name.setter
            def plugin_name(self, value):
                self._plugin_name = value

        # Add the MainActionsPlugin class to the mocked module
        mock_mod.MainActionsPlugin = MainActionsPlugin

        # Use the module name expected by load_plugin
        module_name = 'plugins.action_interactions.default.main_actions.main_actions'

        # Patch PluginBase and call load_plugin
        with patch('core.plugin_base.PluginBase', new=MagicMock()):
            plugin_instance = plugin_manager.load_plugin('plugins', module_name)

            # Check that the plugin was correctly loaded
            assert plugin_instance is not None, "The plugin was not loaded correctly"
            assert isinstance(plugin_instance, MainActionsPlugin)

def test_initialize_plugins(plugin_manager):
    mock_plugin = MagicMock()
    mock_plugin.initialize = MagicMock()
    plugin_manager.plugins = {'CATEGORY': {'SUBCATEGORY': [mock_plugin]}}
    plugin_manager.initialize_plugins()
    mock_plugin.initialize.assert_called_once()

def test_initialize_routes(plugin_manager):
    mock_app = MagicMock()
    mock_router = MagicMock()
    with patch('utils.plugin_manager.plugin_manager.APIRouter', return_value=mock_router):
        mock_plugin_instance = MagicMock()
        mock_plugin_instance.route_methods = ['GET']
        mock_plugin_instance.route_path = '/test'
        mock_plugin_instance.handle_request = MagicMock()
        plugin_manager.plugins = {'USER_INTERACTIONS': {'SUBCATEGORY': [mock_plugin_instance]}}
        plugin_manager.intialize_routes(mock_app)
        mock_router.add_api_route.assert_called_once_with('/test', mock_plugin_instance.handle_request, methods=['get'])
        mock_app.include_router.assert_called_once_with(mock_router)

# Additional test to improve coverage on custom actions from plugin folders
def test_load_custom_actions_from_plugin_folders(plugin_manager, mock_plugins):
    with patch.object(plugin_manager, 'get_plugin', return_value=None) as mock_get_plugin:
        plugin_manager.plugin_configs = mock_plugins
        plugin_manager._load_custom_actions_from_plugin_folders([])
        mock_get_plugin.assert_called()
