from unittest.mock import MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.generate_image import (
    GenerateImage,
)


@pytest.mark.asyncio
async def test_execute_generate_image_success(mock_global_manager):
    action = GenerateImage(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = mock_global_manager.user_interactions_dispatcher

    action_input = ActionInput(action_name="generate_image", parameters={'prompt': 'A beautiful sunset', 'size': '1024x1024'})
    event = MagicMock(spec=IncomingNotificationDataBase)

    mock_global_manager.genai_image_generator_dispatcher.handle_action.return_value = "http://example.com/image.png"

    await action.execute(action_input, event)

    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Generating your image please wait...",
        message_type=MessageType.COMMENT,
        is_internal=False
    )
    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="<http://example.com/image.png|Image>"
    )

@pytest.mark.asyncio
async def test_execute_generate_image_failure(mock_global_manager):
    action = GenerateImage(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = mock_global_manager.user_interactions_dispatcher

    action_input = ActionInput(action_name="generate_image", parameters={'prompt': 'A beautiful sunset', 'size': '1024x1024'})
    event = MagicMock(spec=IncomingNotificationDataBase)

    mock_global_manager.genai_image_generator_dispatcher.handle_action.return_value = "{'Error': 'Something went wrong', 'message': 'Detailed error message'}"

    await action.execute(action_input, event)

    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Generating your image please wait...",
        message_type=MessageType.COMMENT,
        is_internal=False
    )
    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Image generation failed: {'Error': 'Something went wrong', 'message': 'Detailed error message'}",
        is_internal=True  # Updated assertion to reflect internal message
    )

@pytest.mark.asyncio
async def test_execute_generate_image_invalid_url(mock_global_manager):
    action = GenerateImage(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = mock_global_manager.user_interactions_dispatcher

    action_input = ActionInput(action_name="generate_image", parameters={'prompt': 'A beautiful sunset', 'size': '1024x1024'})
    event = MagicMock(spec=IncomingNotificationDataBase)

    mock_global_manager.genai_image_generator_dispatcher.handle_action.return_value = "invalid_url"

    await action.execute(action_input, event)

    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Generating your image please wait...",
        message_type=MessageType.COMMENT,
        is_internal=False
    )
    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Image generation failed: Invalid URL invalid_url",
        is_internal=True  # Updated assertion to reflect internal message
    )

@pytest.mark.asyncio
async def test_execute_generate_image_no_url(mock_global_manager):
    action = GenerateImage(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = mock_global_manager.user_interactions_dispatcher

    action_input = ActionInput(action_name="generate_image", parameters={'prompt': 'A beautiful sunset', 'size': '1024x1024'})
    event = MagicMock(spec=IncomingNotificationDataBase)

    mock_global_manager.genai_image_generator_dispatcher.handle_action.return_value = None

    await action.execute(action_input, event)

    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Generating your image please wait...",
        message_type=MessageType.COMMENT,
        is_internal=False
    )
    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Image generation failed",
        is_internal=True  # Updated assertion to reflect internal message
    )

@pytest.mark.asyncio
async def test_is_valid_url():
    action = GenerateImage(MagicMock())

    assert action.is_valid_url("http://example.com")
    assert action.is_valid_url("https://example.com")
    assert not action.is_valid_url("htp://example.com")
    assert not action.is_valid_url("example.com")
