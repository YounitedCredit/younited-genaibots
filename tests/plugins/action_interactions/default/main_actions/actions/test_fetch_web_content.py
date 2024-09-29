from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.fetch_web_content import (
    FetchWebContent,
)

@pytest.mark.asyncio
async def test_execute_no_url_provided(mock_global_manager):
    action = FetchWebContent(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = AsyncMock()

    action_input = ActionInput(action_name="fetch_web_content", parameters={})
    event = MagicMock(spec=IncomingNotificationDataBase)

    # Execute the action
    await action.execute(action_input, event)

    # Print all calls to send_message for debugging
    print(action.user_interaction_dispatcher.send_message.call_args_list)

    # Assert logger error
    action.logger.error.assert_called_once_with("No URL provided")

    # Adjusting the test to assert the actual user-facing message
    action.user_interaction_dispatcher.send_message.assert_any_call(
        event=event,
        message="Sorry, something went wrong, I didn't receive any url. Try again or contact the bot owner",
        message_type=MessageType.COMMENT,
        action_ref='fetch_web_content'  # Include action_ref
    )


class AsyncContextManagerMock:
    def __init__(self, return_value):
        self._return_value = return_value

    async def __aenter__(self):
        return self._return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.mark.asyncio
@patch('aiohttp.ClientSession')
async def test_execute_with_url(mock_client_session, mock_global_manager):
    action = FetchWebContent(mock_global_manager)
    action.logger = MagicMock()
    action.user_interaction_dispatcher = AsyncMock()
    action.genai_interactions_text_dispatcher = AsyncMock()

    mock_response = MagicMock()
    mock_response.text = AsyncMock(return_value="<html><body>Test Content</body></html>")

    # Mocking session.get to return a context manager
    mock_get = AsyncContextManagerMock(mock_response)
    mock_session = MagicMock()
    mock_session.get.return_value = mock_get

    mock_client_session.return_value = AsyncContextManagerMock(mock_session)

    action_input = ActionInput(action_name="fetch_web_content", parameters={'url': 'http://example.com'})
    event = MagicMock(spec=IncomingNotificationDataBase)

    await action.execute(action_input, event)

    # Vérification intermédiaire
    action.user_interaction_dispatcher.send_message.assert_not_called()  # s'assurer que l'erreur de URL manquant n'est pas levée
    assert mock_session.get.called  # vérifier que l'appel à get a été fait

    # Vérifier que trigger_genai a été appelé
    action.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup_webcontent():
    action = FetchWebContent(MagicMock())

    dirty_text = " This is \n a \t test \r text with   spaces and \n newlines. "
    cleaned_text = action.cleanup_webcontent(dirty_text)

    assert cleaned_text == " This is a test text with spaces and newlines. "
