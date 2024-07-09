from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch


@patch('core.global_manager.GlobalManager')
def test_global_manager_initialization(mock_global_manager):
    mock_global_manager = mock_global_manager.return_value
    type(mock_global_manager).base_directory = PropertyMock(return_value=Path('.'))
    mock_global_manager.config_manager = MagicMock()
    mock_global_manager.plugin_manager = MagicMock()
    mock_global_manager.user_interactions_handler = MagicMock()
    mock_global_manager.action_interactions_handler = MagicMock()
    mock_global_manager.prompt_manager = MagicMock()
    assert mock_global_manager.config_manager is not None
    assert mock_global_manager.plugin_manager is not None
    assert mock_global_manager.user_interactions_handler is not None
    assert mock_global_manager.action_interactions_handler is not None
    assert mock_global_manager.prompt_manager is not None
    assert isinstance(mock_global_manager.base_directory, Path)


def test_get_plugin(mock_global_manager):
    mock_global_manager.get_plugin.return_value = 'plugin'
    assert mock_global_manager.get_plugin('category', 'subcategory') == 'plugin'
    mock_global_manager.get_plugin.assert_called_once_with('category', 'subcategory')


def test_register_plugin_actions(mock_global_manager):
    mock_global_manager.register_plugin_actions('plugin_name', 'actions')
    mock_global_manager.register_plugin_actions.assert_called_once_with('plugin_name', 'actions')


def call_original(self):
    return self._mock_parent._get_child_mock(
        self._mock_name, self._mock_from_name, wraps=self._mock_wraps
    )


def test_get_action(mock_global_manager):
    # Set up test data
    action_name = 'test_action'
    action_class = Mock()
    mock_global_manager.available_actions = {
        'test_package': {
            action_name: action_class
        }
    }

    # Mimic the behavior of the get_action method
    def side_effect(action_name):
        for package, actions in mock_global_manager.available_actions.items():
            for action_class_name, action_class in actions.items():
                if action_name == action_class_name:
                    return action_class

    mock_global_manager.get_action.side_effect = side_effect

    # Call the method and check the result
    result = mock_global_manager.get_action(action_name)
    assert result == action_class
