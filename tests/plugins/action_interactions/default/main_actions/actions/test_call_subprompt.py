import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.call_subprompt import (
    CallSubprompt,
)


@pytest.fixture
def mock_global_manager():
    mock_global_manager = MagicMock()
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.prompt_manager = AsyncMock()
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value="No subprompt found, explain to the user the situation, if you can try to help him rephrase its request, or to contact your administrator.")
    return mock_global_manager

@pytest.fixture
def call_subprompt_instance(mock_global_manager):
    return CallSubprompt(mock_global_manager)

@pytest.fixture
def action_input():
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
        origin="test_origin",
        origin_plugin_name="plugin_name"
    )

@patch('plugins.action_interactions.default.main_actions.actions.call_subprompt.GetPreviousFeedback.get_previous_feedback', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_execute_success(mock_get_feedback, mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value="test_subprompt_content")
    mock_get_feedback.return_value = "test_feedback"

    await call_subprompt_instance.execute(action_input, incoming_notification)

    call_subprompt_instance.user_interactions_dispatcher.send_message.assert_any_call(
        event=incoming_notification,
        message="Invoking subprompt: [test_subprompt]...",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

    # Vérification des attributs modifiés
    expected_notification = copy.deepcopy(incoming_notification)
    expected_notification.text = (
        "Here's updated instruction that you must consider as system instruction: test_subprompt_content. \n\n"
        "Now process this previous user input based on this new knowledge and act according to this provided workflow, "
        "and take into account the previous feedback on this: test_feedback"
    )

    # Comparer le texte mis à jour avant l'appel à trigger_genai
    updated_notification = call_subprompt_instance.genai_interactions_text_dispatcher.trigger_genai.call_args[1]['event']
    assert "Here's updated instruction that you must consider as system instruction:" in updated_notification.text
    assert "and take into account the previous feedback on this:" in updated_notification.text


@patch('plugins.action_interactions.default.main_actions.actions.call_subprompt.GetPreviousFeedback.get_previous_feedback', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_execute_missing_value(mock_get_feedback, mock_global_manager, call_subprompt_instance, incoming_notification):
    action_input = ActionInput(action_name='call_subprompt', parameters={})

    await call_subprompt_instance.execute(action_input, incoming_notification)

    call_subprompt_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="I didn't find the specific instruction sorry about that :-/, this is certainly an issue with my instructions, contact my administrator.",
        message_type=MessageType.TEXT,
        is_internal=False
    )

@patch('plugins.action_interactions.default.main_actions.actions.call_subprompt.GetPreviousFeedback.get_previous_feedback', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_execute_subprompt_not_found(mock_get_feedback, mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(return_value=None)

    await call_subprompt_instance.execute(action_input, incoming_notification)

    expected_notification = copy.deepcopy(incoming_notification)
    expected_notification.text = (
        "No subpromtp found, explain to the user the situation, if you can try to help him rephrase its request, "
        "or to contact your administrator."
    )

    # Comparer le texte mis à jour avant l'appel à trigger_genai
    updated_notification = call_subprompt_instance.genai_interactions_text_dispatcher.trigger_genai.call_args[1]['event']
    assert "Here's updated instruction that you must consider as system instruction:" in updated_notification.text
    assert "and take into account the previous feedback on this:" in updated_notification.text

@patch('plugins.action_interactions.default.main_actions.actions.call_subprompt.GetPreviousFeedback.get_previous_feedback', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_execute_general_error(mock_get_feedback, mock_global_manager, call_subprompt_instance, action_input, incoming_notification):
    mock_global_manager.prompt_manager.get_sub_prompt = AsyncMock(side_effect=Exception("General error"))

    await call_subprompt_instance.execute(action_input, incoming_notification)

    call_subprompt_instance.logger.exception.assert_called_with("An error occurred: General error")
