import sys
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.action_interactions.action_interactions_plugin_base import (
    ActionInteractionsPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)

class TestActionInteractionsPlugin(ActionInteractionsPluginBase):
    def __init__(self, global_manager):
        super().__init__(global_manager)
        self._plugin_name = "test_plugin"

    @property
    def plugin_name(self):
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

@pytest.fixture
def concrete_plugin(mock_global_manager):
    return TestActionInteractionsPlugin(global_manager=mock_global_manager)

def test_load_actions(concrete_plugin, mock_global_manager):
    actions_path = Path('/fake/path/to/actions')

    class MockAction(ActionBase):
        def __init__(self, global_manager):
            super().__init__(global_manager)

        def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
            return "Mock result"

    mock_module = MagicMock()
    mock_module.MockAction = MockAction

    with patch('pkgutil.iter_modules', return_value=[(None, 'test_module', None)]), \
         patch.object(concrete_plugin, '_import_module', return_value=mock_module), \
         patch.object(concrete_plugin, '_process_module'), \
         patch.object(concrete_plugin, '_log_loaded_actions'), \
         patch.dict(sys.modules, {'__main__': MagicMock(__package__='core.action_interactions')}):

        concrete_plugin.load_actions(actions_path)

        concrete_plugin._import_module.assert_called_once()
        concrete_plugin._process_module.assert_called_once_with(mock_module, [])
        concrete_plugin._log_loaded_actions.assert_called_once()

def test_import_module(concrete_plugin):
    mock_actions_path = Path('/fake/actions/path')
    mock_module_name = 'test_module'
    mock_root_directory = Path('/fake/actions')  # Changé pour être un parent de mock_actions_path

    with patch('importlib.import_module', return_value='mock_module') as mock_import:
        result = concrete_plugin._import_module(mock_actions_path, mock_module_name, mock_root_directory)
        assert result == 'mock_module'
        mock_import.assert_called_once_with('path.test_module')

    with patch('importlib.import_module', side_effect=ImportError('Mock import error')), \
         patch.object(concrete_plugin.logger, 'error') as mock_logger_error:
        result = concrete_plugin._import_module(mock_actions_path, mock_module_name, mock_root_directory)
        assert result is None
        mock_logger_error.assert_called_once()

def test_process_module(concrete_plugin):
    mock_module = MagicMock()
    loaded_actions = []

    class MockAction(ActionBase):
        pass

    with patch('inspect.getmembers', return_value=[('MockAction', MockAction)]), \
         patch.object(concrete_plugin, '_is_valid_action_class', return_value=True), \
         patch.object(concrete_plugin, '_add_action_class'):
        concrete_plugin._process_module(mock_module, loaded_actions)
        concrete_plugin._is_valid_action_class.assert_called_once_with(MockAction)
        concrete_plugin._add_action_class.assert_called_once_with(MockAction, loaded_actions)

def test_is_valid_action_class(concrete_plugin):
    class ValidAction(ActionBase):
        pass

    class InvalidAction:
        pass

    assert concrete_plugin._is_valid_action_class(ValidAction) == True
    assert concrete_plugin._is_valid_action_class(InvalidAction) == False
    assert concrete_plugin._is_valid_action_class(ActionBase) == False

def test_add_action_class(concrete_plugin, mock_global_manager):
    class TestAction(ActionBase):
        def __init__(self, global_manager):
            super().__init__(global_manager)
        
        def execute(self, action_input, event):
            # Implémentation factice de la méthode execute
            return "Test execution"

    # Réinitialiser available_actions pour ce test
    mock_global_manager.available_actions = {}
    concrete_plugin.global_manager = mock_global_manager

    loaded_actions = []

    # Simuler le package correct
    test_package = 'core.action_interactions'

   
    with patch('core.action_interactions.action_interactions_plugin_base.__package__', test_package):
        concrete_plugin._add_action_class(TestAction, loaded_actions)

    # Vérifications
    assert test_package in mock_global_manager.available_actions, f"{test_package} n'a pas été ajouté aux actions disponibles"
    
    if test_package in mock_global_manager.available_actions:
        print(f"Contenu de {test_package}: {mock_global_manager.available_actions[test_package]}")
    
    assert 'TestAction' in mock_global_manager.available_actions[test_package], "TestAction n'a pas été ajouté au package"
    assert isinstance(mock_global_manager.available_actions[test_package]['TestAction'], TestAction), "L'instance de TestAction n'a pas été correctement créée"
    assert 'TestAction' in loaded_actions, "Le nom de l'action n'a pas été ajouté à loaded_actions"

def test_log_loaded_actions(concrete_plugin):
    loaded_actions = ['Action1', 'Action2']
    with patch.object(concrete_plugin.logger, 'debug') as mock_logger_debug:
        concrete_plugin._log_loaded_actions(loaded_actions)
        mock_logger_debug.assert_called_once()

class ValidActions(Enum):
    TEST = "Test"

class TestActions(Enum):
    TEST = "Test"
    INVALID = "Invalid"
    
def test_validate_actions(concrete_plugin):
    # Créer une action valide
    class TestAction(ActionBase):
        def execute(self, item):
            pass

    # Créer une classe invalide qui n'hérite pas de ActionBase
    class InvalidAction:
        pass

    # Test avec seulement l'action valide
    setattr(concrete_plugin, 'TestAction', TestAction)
    concrete_plugin._Actions = ValidActions
    concrete_plugin.validate_actions()  # Ne devrait pas lever d'exception

    # Test avec une action invalide
    setattr(concrete_plugin, 'InvalidAction', InvalidAction)
    concrete_plugin._Actions = TestActions
    with pytest.raises(ValueError, match="No valid action class found for action 'Invalid'"):
        concrete_plugin.validate_actions()

    # Test avec une action manquante
    delattr(concrete_plugin, 'TestAction')
    with pytest.raises(ValueError, match="No valid action class found for action 'Test'"):
        concrete_plugin.validate_actions()

@pytest.mark.asyncio
async def test_execute_action(concrete_plugin):
    class TestAction(ActionBase):
        def __init__(self, global_manager):
            super().__init__(global_manager)

        def execute(self, item):
            return 'result'

    # Simuler l'ajout de l'action au plugin
    setattr(concrete_plugin, 'TestAction', TestAction)

    # Créer un mock pour l'instance de TestAction
    mock_action_instance = MagicMock(spec=TestAction)
    mock_action_instance.execute.return_value = 'result'

    # Patcher la classe TestAction pour qu'elle retourne notre mock d'instance
    with patch.object(TestAction, '__new__', return_value=mock_action_instance):
        result = await concrete_plugin.execute_action('Test', 'item')
        assert result == 'result'

        # Vérifier que execute a été appelé avec le bon argument
        mock_action_instance.execute.assert_called_once_with('item')

    with pytest.raises(ValueError, match="No valid action class found for action 'Invalid'"):
        await concrete_plugin.execute_action('Invalid', 'item')
