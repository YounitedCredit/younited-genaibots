from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.get_previous_feedback import (
    GetPreviousFeedback,
)


@pytest.fixture
def mock_backend_internal_data_processing_dispatcher():
    mock_dispatcher = MagicMock()
    mock_dispatcher.read_data_content = AsyncMock()
    mock_dispatcher.feedbacks = MagicMock()
    return mock_dispatcher

def create_mock_incoming_notification():
    return IncomingNotificationDataBase(
        timestamp="2023-01-01 00:00:00",
        converted_timestamp="2023-01-01 00:00:00",
        event_label="test_event",
        channel_id="test_channel",
        thread_id="test_thread",
        response_id="test_response",
        user_name="Test User",
        user_email="test@example.com",
        user_id="test_user_id",
        is_mention=False,
        text="Test message",
        origin="test_origin"
    )

@pytest.fixture
def get_previous_feedback_action(mock_global_manager, mock_backend_internal_data_processing_dispatcher):
    mock_global_manager.backend_internal_data_processing_dispatcher = mock_backend_internal_data_processing_dispatcher
    return GetPreviousFeedback(mock_global_manager)

@pytest.mark.asyncio
async def test_get_previous_feedback_no_general_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    category = "test_category"
    sub_category = "test_sub_category"
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = [Exception("No general feedback"), "Specific feedback content"]

    result = await get_previous_feedback_action.get_previous_feedback(category, sub_category)

    assert result == "Don't create another feedback from this as this is an automated message containing our insights from past interactions in the context of test_category test_sub_category :[Specific feedback content]. Based on these informations follow next step of your current workflow."

@pytest.mark.asyncio
async def test_get_previous_feedback_no_specific_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    category = "test_category"
    sub_category = "test_sub_category"
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = ["General feedback content", Exception("No specific feedback")]

    result = await get_previous_feedback_action.get_previous_feedback(category, sub_category)

    assert result is None

@pytest.mark.asyncio
async def test_get_previous_feedback_with_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    category = "test_category"
    sub_category = "test_sub_category"
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = ["General feedback content", "Specific feedback content"]

    result = await get_previous_feedback_action.get_previous_feedback(category, sub_category)

    assert result == "Don't create another feedback from this as this is an automated message containing our insights from past interactions in the context of test_category test_sub_category :[General feedback content\nSpecific feedback content]. Based on these informations follow next step of your current workflow."

@pytest.mark.asyncio
async def test_get_previous_feedback_no_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    category = "test_category"
    sub_category = "test_sub_category"
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = [Exception("No general feedback"), Exception("No specific feedback")]

    result = await get_previous_feedback_action.get_previous_feedback(category, sub_category)

    assert result is None

@pytest.mark.asyncio
async def test_execute_with_existing_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    action_input = ActionInput(action_name="GetPreviousFeedback", parameters={"Category": "test_category", "SubCategory": "test_sub_category"})
    event = create_mock_incoming_notification()
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = ["General feedback", "Specific feedback"]

    await get_previous_feedback_action.execute(action_input, event)

    # Assert that the correct methods were called
    get_previous_feedback_action.user_interaction_dispatcher.send_message.assert_called()
    get_previous_feedback_action.genai_interactions_text_dispatcher.trigger_genai.assert_called()

@pytest.mark.asyncio
async def test_execute_without_feedback(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    action_input = ActionInput(action_name="GetPreviousFeedback", parameters={"Category": "test_category", "SubCategory": "test_sub_category"})
    event = create_mock_incoming_notification()
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = [Exception("No feedback")]

    await get_previous_feedback_action.execute(action_input, event)

    # Assert that the correct methods were called
    get_previous_feedback_action.user_interaction_dispatcher.send_message.assert_called()
    get_previous_feedback_action.genai_interactions_text_dispatcher.trigger_genai.assert_called()

@pytest.mark.asyncio
async def test_execute_with_error(get_previous_feedback_action, mock_backend_internal_data_processing_dispatcher):
    action_input = ActionInput(action_name="GetPreviousFeedback", parameters={"Category": "test_category", "SubCategory": "test_sub_category"})
    event = create_mock_incoming_notification()
    mock_backend_internal_data_processing_dispatcher.read_data_content.side_effect = [Exception("Test error"), Exception("Test error")]

    # Mock user_interaction_dispatcher and genai_interactions_text_dispatcher
    get_previous_feedback_action.user_interaction_dispatcher = AsyncMock()
    get_previous_feedback_action.genai_interactions_text_dispatcher = AsyncMock()

    await get_previous_feedback_action.execute(action_input, event)

    # Check all calls to send_message
    calls = get_previous_feedback_action.user_interaction_dispatcher.send_message.call_args_list
    assert len(calls) >= 2, f"Expected at least 2 calls to send_message, got {len(calls)}"

    # Check for the error message
    error_message_call = next((call for call in calls if ":warningSorry there was an issue gathering previous feedback" in call.kwargs.get('message', '')), None)
    assert error_message_call is not None, "Error message not found in send_message calls"
    assert error_message_call.kwargs['message_type'] == MessageType.TEXT

    # Check for the comment message
    comment_message_call = next((call for call in calls if "Error gathering previous feedback found for:" in call.kwargs.get('message', '')), None)
    assert comment_message_call is not None, "Comment message not found in send_message calls"
    assert comment_message_call.kwargs['message_type'] == MessageType.COMMENT

    # Check that genai_interactions_text_dispatcher.trigger_genai was called twice
    assert get_previous_feedback_action.genai_interactions_text_dispatcher.trigger_genai.call_count == 2, \
        f"Expected trigger_genai to be called 2 times, but it was called {get_previous_feedback_action.genai_interactions_text_dispatcher.trigger_genai.call_count} times"
