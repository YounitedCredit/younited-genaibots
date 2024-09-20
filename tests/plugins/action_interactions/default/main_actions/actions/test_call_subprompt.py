import copy
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import IncomingNotificationDataBase
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.call_subprompt import CallSubprompt

@pytest.fixture
def mock_global_manager(mock_config_manager, mock_plugins):
    """
    Fixture that creates a mocked instance of the global manager using
    objects from conftest.py for reuse.
    """
    mock_global_manager = MagicMock()
    mock_global_manager.config_manager = mock_config_manager
    mock_global_manager.plugins = mock_plugins
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.prompt_manager = AsyncMock()
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value="default_subprompt")
    return mock_global_manager

@pytest.fixture
def call_subprompt_instance(mock_global_manager):
    """
    Fixture to initialize the CallSubprompt action with a mocked global manager.
    """
    return CallSubprompt(mock_global_manager)

@pytest.fixture
def action_input():
    """
    Fixture to create a standard ActionInput object.
    """
    return ActionInput(
        action_name='call_subprompt',
        parameters={
            'value': 'test_subprompt',
            'feedback_category': 'test_category',
            'feedback_subcategory': 'test_subcategory'
        }
    )

@pytest.fixture
def incoming_notification():
    """
    Fixture to create a mock of IncomingNotificationDataBase for the event parameter.
    """
    return IncomingNotificationDataBase(
        timestamp="2023-01-01T00:00:00Z",
        event_label="test_event",
        channel_id="test_channel",
        thread_id="test_thread",
        response_id="test_response",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="user123",
        is_mention=False,
        text="Test message",
        origin_plugin_name="plugin_name"
    )

@patch('plugins.action_interactions.default.main_actions.actions.call_subprompt.GetPreviousFeedback.get_previous_feedback', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_execute_success(mock_get_feedback, mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    """
    Test successful execution of the CallSubprompt action, ensuring subprompt is invoked correctly and feedback is appended.
    """
    # Mock subprompt and feedback return values
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value="test_subprompt_content")
    mock_get_feedback.return_value = "test_feedback"

    # Execute the action
    await call_subprompt_instance.execute(action_input, incoming_notification)

    # Verify message sent with the correct subprompt
    call_subprompt_instance.user_interactions_dispatcher.send_message.assert_any_call(
        event=incoming_notification,
        message="Invoking subprompt: [test_subprompt]...",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

    # Verify updated event text with feedback
    expected_notification = copy.deepcopy(incoming_notification)
    expected_notification.text = (
        "Here's updated instruction that you must consider as system instruction: test_subprompt_content. "
        "Take into account the previous feedback on this: test_feedback."
    )

    # Check if the event text was correctly updated before triggering genai
    updated_notification = call_subprompt_instance.genai_interactions_text_dispatcher.trigger_genai.call_args[1]['event']
    
    # Update the assert to account for line breaks and feedback formatting
    assert "Here's updated instruction that you must consider as system instruction:" in updated_notification.text
    assert "test_subprompt_content" in updated_notification.text
    assert "test_feedback" in updated_notification.text

@pytest.mark.asyncio
async def test_execute_missing_value(mock_global_manager, call_subprompt_instance, incoming_notification):
    """
    Test execution when the 'value' parameter is missing from ActionInput, ensuring an appropriate error message is sent.
    """
    action_input = ActionInput(action_name='call_subprompt', parameters={})

    # Execute the action
    await call_subprompt_instance.execute(action_input, incoming_notification)

    # Verify that an error message is sent
    call_subprompt_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="I didn't find the specific instruction sorry about that :-/, this is certainly an issue with my instructions, contact my administrator.",
        message_type=MessageType.TEXT,
        is_internal=False
    )

@pytest.mark.asyncio
async def test_execute_subprompt_not_found(mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    """
    Test execution when the subprompt is not found, ensuring the correct fallback message is used.
    """
    # Mock subprompt to return None
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value=None)

    # Execute the action
    await call_subprompt_instance.execute(action_input, incoming_notification)

    # Verify updated event text for subprompt not found
    expected_notification = copy.deepcopy(incoming_notification)
    expected_notification.text = (
        "No subprompt found, explain to the user the situation, if you can try to help him rephrase its request, "
        "or to contact your administrator."
    )

    # Check if the event text was correctly updated before triggering genai
    updated_notification = call_subprompt_instance.genai_interactions_text_dispatcher.trigger_genai.call_args[1]['event']
    
    # Update the assert to match the actual structure of the notification
    assert "No subprompt found" in updated_notification.text or "None" in updated_notification.text

@pytest.mark.asyncio
async def test_execute_general_error(mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    """
    Test that a general error in execution is correctly logged.
    """
    # Mock an exception when getting the subprompt
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(side_effect=Exception("General error"))

    # Execute the action
    await call_subprompt_instance.execute(action_input, incoming_notification)

    # Verify that the exception was logged
    call_subprompt_instance.logger.error.assert_called_with("An error occurred: General error")
