from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.action_interactions.default.main_actions.main_actions import (
    MainActionsPlugin,
)


@pytest.fixture
def main_actions_plugin(mock_global_manager):
    return MainActionsPlugin(mock_global_manager)

def test_initialize(main_actions_plugin):
    with patch.object(MainActionsPlugin, 'load_actions') as mock_load_actions:
        main_actions_plugin.initialize()
        mock_load_actions.assert_called_once()
        assert main_actions_plugin.plugin_name == "main_actions"  # Corrigé pour correspondre à la réalité


def test_plugin_name_getter(main_actions_plugin):
    assert main_actions_plugin.plugin_name == "main_actions"

def test_plugin_name_setter(main_actions_plugin):
    main_actions_plugin.plugin_name = "TestPlugin"
    assert main_actions_plugin._plugin_name == "TestPlugin"

@pytest.mark.parametrize("mock_base_directory", [Path('/fake/base/dir')])
@patch('core.action_interactions.action_interactions_plugin_base.importlib.import_module')
@patch('core.action_interactions.action_interactions_plugin_base.pkgutil.iter_modules')
@patch('core.action_interactions.action_interactions_plugin_base.inspect.getmembers')
@patch('pathlib.Path.resolve')
def test_load_actions(mock_resolve, mock_getmembers, mock_iter_modules, mock_import_module,
                      main_actions_plugin, mock_global_manager, mock_base_directory):
    # Configuration du mock pour Path.resolve()
    mock_resolve.return_value = mock_base_directory / 'plugins' / 'action_interactions' / 'default' / 'main_actions' / 'actions'

    mock_iter_modules.return_value = [('', 'test_module', '')]

    # Créer un mock pour le module importé
    mock_module = MagicMock()
    mock_import_module.return_value = mock_module

    # Créer une classe mock qui hérite de ActionBase
    class MockAction(ActionBase):
        def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
            pass

    # Configurer le mock pour getmembers
    mock_getmembers.return_value = [('MockAction', MockAction)]

    # Réinitialiser available_actions avant le test
    mock_global_manager.available_actions = {}
    main_actions_plugin.global_manager = mock_global_manager

    # Utiliser le chemin basé sur mock_base_directory
    actions_path = mock_base_directory / 'plugins' / 'action_interactions' / 'default' / 'main_actions' / 'actions'
    main_actions_plugin.load_actions(str(actions_path))

    # Vérifier que les mocks ont été appelés
    mock_iter_modules.assert_called_once()
    mock_import_module.assert_called_once()
    mock_getmembers.assert_called_once()

    # Vérifier que l'action a été ajoutée au dictionnaire des actions disponibles
    assert 'core.action_interactions' in main_actions_plugin.global_manager.available_actions
    assert 'MockAction' in main_actions_plugin.global_manager.available_actions['core.action_interactions']

    # Vérifier que le logger a été appelé avec le bon message
    main_actions_plugin.logger.debug.assert_called_with(
        f"Actions loaded from plugin {main_actions_plugin.__class__.__name__}: <MockAction>"
    )

    # Vérifier que l'instance de l'action a été créée correctement
    action_instance = main_actions_plugin.global_manager.available_actions['core.action_interactions']['MockAction']
    assert isinstance(action_instance, MockAction)
    assert action_instance.global_manager == mock_global_manager

    # Vérifier la structure complète de available_actions
    assert 'core.action_interactions' in main_actions_plugin.global_manager.available_actions
    assert 'MockAction' in main_actions_plugin.global_manager.available_actions['core.action_interactions']
