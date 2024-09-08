import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from core.action_interactions.custom_actions_from_backend_plugin import CustomActionsFromBackendPlugin

@pytest.mark.asyncio
async def test_initialize(mock_global_manager):
    """
    Test the initialize method of CustomActionsFromBackendPlugin.
    It should set the plugin_name and schedule the loading of actions.
    """
    plugin = CustomActionsFromBackendPlugin(mock_global_manager)

    with patch.object(plugin.logger, 'info') as mock_logger_info, \
         patch.object(plugin, 'load_actions', new_callable=AsyncMock) as mock_load_actions:
        # Call the initialize method
        plugin.initialize()
        
        # Ensure that plugin_name is set correctly
        assert plugin.plugin_name == "custom_actions_from_backend"
        
        # Ensure that the logger was called with the correct message
        mock_logger_info.assert_called_with(f"Initializing actions for plugin custom_actions_from_backend from backend.")
        
        # Ensure that load_actions was scheduled to run asynchronously
        mock_load_actions.assert_called_once()


@pytest.mark.asyncio
async def test_load_actions_no_files(mock_global_manager):
    """
    Test the load_actions method when no custom action files are found in the backend.
    """
    plugin = CustomActionsFromBackendPlugin(mock_global_manager)
    
    # Mock the backend dispatcher to return no files
    mock_global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=[])

    with patch.object(plugin.logger, 'warning') as mock_logger_warning, \
         patch.object(plugin, '_log_loaded_actions', new_callable=MagicMock) as mock_log_loaded_actions:
        # Call the load_actions method
        await plugin.load_actions()
        
        # Ensure the warning logger was called to indicate no custom actions found
        mock_logger_warning.assert_called_with("No custom actions found in backend container 'custom_actions'")
        
        # Ensure that _log_loaded_actions was called with an empty list
        mock_log_loaded_actions.assert_called_once_with([])


@pytest.mark.asyncio
async def test_load_actions_with_files(mock_global_manager):
    """
    Test the load_actions method when custom action files are found and processed.
    """
    plugin = CustomActionsFromBackendPlugin(mock_global_manager)
    
    # Mock the backend dispatcher to return a list of action files
    mock_global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(return_value=['action1', 'action2'])
    
    # Mock the backend dispatcher to return action file content
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=[
        "def action1(): pass",  # Mock content for action1
        "def action2(): pass"   # Mock content for action2
    ])
    
    with patch.object(plugin.logger, 'info') as mock_logger_info, \
         patch.object(plugin, '_process_module', new_callable=MagicMock) as mock_process_module, \
         patch.object(plugin, '_log_loaded_actions', new_callable=MagicMock) as mock_log_loaded_actions:
        # Call the load_actions method
        await plugin.load_actions()
        
        # Ensure that the info logger was called for fetching actions
        mock_logger_info.assert_any_call("Fetching custom actions from backend container: custom_actions")
        
        # Ensure that _process_module was called twice (for action1 and action2)
        assert mock_process_module.call_count == 2
        
        # Ensure that _log_loaded_actions was called with the correct number of loaded actions
        mock_log_loaded_actions.assert_called_once()


@pytest.mark.asyncio
async def test_load_actions_error_handling(mock_global_manager):
    """
    Test the load_actions method when an error occurs during action loading.
    """
    plugin = CustomActionsFromBackendPlugin(mock_global_manager)
    
    # Mock the backend dispatcher to raise an exception
    mock_global_manager.backend_internal_data_processing_dispatcher.list_container_files = AsyncMock(side_effect=Exception("Backend error"))
    
    with patch.object(plugin.logger, 'error') as mock_logger_error:
        # Call the load_actions method and expect no exception raised
        await plugin.load_actions()
        
        # Ensure the error logger was called with the correct message
        mock_logger_error.assert_called_with("Error while loading actions from backend: Backend error")

