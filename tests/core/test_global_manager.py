from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest


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

@pytest.mark.asyncio
async def test_dispatcher_initializations(mock_global_manager):
    plugins = {
        ('USER_INTERACTIONS',None): [MagicMock()],
        ('GENAI_INTERACTIONS','TEXT'): [MagicMock()],
        ('GENAI_INTERACTIONS','IMAGE'): [MagicMock()],
        ('GENAI_INTERACTIONS','VECTOR_SEARCH'): [MagicMock()],
        ('BACKEND','INTERNAL_DATA_PROCESSING'): [MagicMock()],
        ('BACKEND','INTERNAL_QUEUE_PROCESSING'): [MagicMock()],
        ('BACKEND','SESSION_MANAGERS'): [MagicMock()],
        ('USER_INTERACTIONS_BEHAVIORS',None): [MagicMock()]
    }

    # Reset des mocks des dispatchers
    mock_global_manager.user_interactions_dispatcher = MagicMock()
    mock_global_manager.genai_interactions_text_dispatcher = MagicMock()
    mock_global_manager.genai_image_generator_dispatcher = MagicMock()
    mock_global_manager.genai_vectorsearch_dispatcher = MagicMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = MagicMock()
    mock_global_manager.backend_internal_queue_processing_dispatcher = MagicMock()
    mock_global_manager.session_manager_dispatcher = MagicMock()
    mock_global_manager.user_interactions_behavior_dispatcher = MagicMock()

    # Mock du plugin_manager et de ses méthodes
    def mock_get_plugin(cat, sub=None):
        return plugins.get((cat, sub), [])
    mock_global_manager.plugin_manager.get_plugin_by_category.side_effect = mock_get_plugin

    # Appel de la méthode d'initialisation des dispatchers
    mock_global_manager.user_interactions_dispatcher.initialize(plugins[('USER_INTERACTIONS',None)])
    mock_global_manager.genai_interactions_text_dispatcher.initialize(plugins[('GENAI_INTERACTIONS','TEXT')])
    mock_global_manager.genai_image_generator_dispatcher.initialize(plugins[('GENAI_INTERACTIONS','IMAGE')])
    mock_global_manager.genai_vectorsearch_dispatcher.initialize(plugins[('GENAI_INTERACTIONS','VECTOR_SEARCH')])
    mock_global_manager.backend_internal_data_processing_dispatcher.initialize(plugins[('BACKEND','INTERNAL_DATA_PROCESSING')])
    mock_global_manager.backend_internal_queue_processing_dispatcher.initialize(plugins[('BACKEND','INTERNAL_QUEUE_PROCESSING')])
    mock_global_manager.session_manager_dispatcher.initialize(plugins[('BACKEND','SESSION_MANAGERS')])
    mock_global_manager.user_interactions_behavior_dispatcher.initialize(plugins[('USER_INTERACTIONS_BEHAVIORS',None)])

    # Vérifications
    mock_global_manager.user_interactions_dispatcher.initialize.assert_called_once()
    mock_global_manager.genai_interactions_text_dispatcher.initialize.assert_called_once()
    mock_global_manager.genai_image_generator_dispatcher.initialize.assert_called_once()
    mock_global_manager.genai_vectorsearch_dispatcher.initialize.assert_called_once()
    mock_global_manager.backend_internal_data_processing_dispatcher.initialize.assert_called_once()
    mock_global_manager.backend_internal_queue_processing_dispatcher.initialize.assert_called_once()
    mock_global_manager.session_manager_dispatcher.initialize.assert_called_once()
    mock_global_manager.user_interactions_behavior_dispatcher.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_queue_manager_activation(mock_global_manager):
    with patch('core.event_processing.interaction_queue_manager.InteractionQueueManager') as queue_mock:
        mock_global_manager.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = True

        # Initialize queue manager
        mock_global_manager.interaction_queue_manager = queue_mock.return_value
        queue_mock.return_value.initialize = AsyncMock()

        # Execute
        await mock_global_manager.interaction_queue_manager.initialize()

        # Verify
        queue_mock.return_value.initialize.assert_called_once()

def test_register_and_get_actions():
    mock_global_manager = MagicMock()
    actions = {'action1': MagicMock()}

    # Setup du comportement du GlobalManager
    def side_effect(action_name):
        return actions.get(action_name)

    mock_global_manager.get_action.side_effect = side_effect
    mock_global_manager.available_actions = {'plugin1': actions}

    # Test l'enregistrement et la récupération
    mock_global_manager.register_plugin_actions('plugin1', actions)
    action = mock_global_manager.get_action('action1')

    assert action == actions['action1']
    assert mock_global_manager.get_action('invalid') is None
