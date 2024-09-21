from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.user_interactions.instant_messaging.slack.utils.slack_output_handler import (
    SlackOutputHandler,
)
import aiohttp

class AsyncContextManagerMock:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

@pytest.fixture
def slack_config():
    class MockSlackConfig:
        SLACK_API_URL = "https://slack.com/api/"
        SLACK_BOT_TOKEN = "xoxb-1234"
        SLACK_BOT_USER_TOKEN = "xoxp-5678"

    return MockSlackConfig()

@pytest.fixture
def slack_output_handler(mock_global_manager, slack_config):
    return SlackOutputHandler(global_manager=mock_global_manager, slack_config=slack_config)

@pytest.fixture
def slack_output_handler(mock_global_manager, slack_config):
    return SlackOutputHandler(global_manager=mock_global_manager, slack_config=slack_config)

@pytest.mark.asyncio
async def test_add_reaction(slack_output_handler, mocker):
    mock_client = mocker.patch.object(slack_output_handler.client, 'reactions_add', new_callable=AsyncMock)
    await slack_output_handler.add_reaction("CHANNEL_ID", "1620834875.000400", "thumbsup")
    mock_client.assert_called_once_with(channel="CHANNEL_ID", timestamp="1620834875.000400", name="thumbsup")

@pytest.mark.asyncio
async def test_remove_reaction(slack_output_handler, mocker):
    mock_client = mocker.patch.object(slack_output_handler.client, 'reactions_remove', new_callable=AsyncMock)
    await slack_output_handler.remove_reaction("CHANNEL_ID", "1620834875.000400", "thumbsup")
    mock_client.assert_called_once_with(channel="CHANNEL_ID", timestamp="1620834875.000400", name="thumbsup")

@pytest.mark.asyncio
async def test_send_slack_message(slack_output_handler):
    with patch("aiohttp.ClientSession", autospec=True) as MockClientSession:
        mock_session = MockClientSession.return_value
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_session.post.return_value = AsyncContextManagerMock(mock_response)

        response = await slack_output_handler.send_slack_message(
            "CHANNEL_ID", "1620834875.000400", "Hello World"
        )
        assert response["ok"] is True

        mock_session.post.assert_called_once_with(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': 'Bearer xoxb-1234'},
            json={
                'channel': 'CHANNEL_ID',
                'thread_ts': '1620834875.000400',
                'blocks': '[{"type": "section", "text": {"type": "mrkdwn", "text": "Hello World"}}]'
            }
        )

@pytest.mark.asyncio
async def test_upload_file_to_slack(slack_output_handler, mocker):
    mock_send_message = mocker.patch.object(slack_output_handler, 'send_slack_message', new_callable=AsyncMock)
    mock_client = mocker.patch.object(slack_output_handler.client, 'files_upload_v2', new_callable=MagicMock)

    # Configure the mock to return a MagicMock with ok attribute
    mock_response = MagicMock(ok=True)
    mock_client.return_value = mock_response

    event = MagicMock(spec=IncomingNotificationDataBase)
    event.channel_id = "CHANNEL_ID"
    event.thread_id = "1620834875.000400"

    # Appeler la méthode upload_file_to_slack
    result = await slack_output_handler.upload_file_to_slack(event, "file_content", "filename.txt", "title")

    # Vérifier que le résultat est correct
    assert result.ok
    mock_send_message.assert_called_with("CHANNEL_ID", "1620834875.000400", "uploading file filename.txt and processing it...", MessageType.COMMENT)
    mock_client.assert_called_once_with(channel="CHANNEL_ID", thread_ts="1620834875.000400", title="title", filename="filename.txt", content="file_content")

@pytest.mark.asyncio
async def test_add_reaction_error(slack_output_handler, mocker):
    mock_client = mocker.patch.object(slack_output_handler.client, 'reactions_add')
    mock_client.side_effect = SlackApiError(message="", response={"error": "already_reacted"})
    mock_logger = mocker.patch.object(slack_output_handler.logger, 'debug')

    await slack_output_handler.add_reaction("CHANNEL_ID", "1620834875.000400", "thumbsup")

    mock_logger.assert_called_once_with("Already reacted. Skipping.")

@pytest.mark.asyncio
async def test_remove_reaction_error(slack_output_handler, mocker):
    mock_client = mocker.patch.object(slack_output_handler.client, 'reactions_remove')
    mock_client.side_effect = SlackApiError(message="", response={"error": "no_reaction"})
    mock_logger = mocker.patch.object(slack_output_handler.logger, 'debug')

    await slack_output_handler.remove_reaction("CHANNEL_ID", "1620834875.000400", "thumbsup")

    mock_logger.assert_called_once_with("No reaction to remove. Skipping.")

@pytest.mark.asyncio
@pytest.mark.parametrize("message_type", [MessageType.TEXT, MessageType.CODEBLOCK, MessageType.COMMENT])
async def test_send_slack_message_types(slack_output_handler, message_type):
    with patch("aiohttp.ClientSession", autospec=True) as MockClientSession:
        mock_session = MockClientSession.return_value
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        # Set up session.post to return an async context manager
        mock_session.post.return_value = AsyncContextManagerMock(mock_response)

        # Execute the function under test
        await slack_output_handler.send_slack_message(
            "CHANNEL_ID", "1620834875.000400", "Message", message_type, "Title"
        )

        # Ensure 'post' was called
        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_send_slack_message_file_type(slack_output_handler):
    with patch("aiohttp.ClientSession", autospec=True) as MockClientSession:
        mock_session = MockClientSession.return_value
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})

        mock_session.post.return_value = AsyncContextManagerMock(mock_response)

        await slack_output_handler.send_slack_message(
            "CHANNEL_ID", "1620834875.000400", "Message", MessageType.FILE, "Title"
        )

        mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_send_slack_message_custom_type(slack_output_handler, mocker):
    mock_post = mocker.patch("requests.post", return_value=MagicMock(status_code=200))
    with pytest.raises(ValueError) as exc_info:
        await slack_output_handler.send_slack_message("CHANNEL_ID", "1620834875.000400", "Message", MessageType.CUSTOM, "Title")
    assert "Invalid message type" in str(exc_info.value)

@pytest.mark.asyncio
async def test_upload_file_to_slack_error(slack_output_handler, mocker):
    mock_send_message = mocker.patch.object(slack_output_handler, 'send_slack_message', new_callable=AsyncMock)
    mock_client = mocker.patch.object(slack_output_handler.client, 'files_upload_v2')
    mock_client.side_effect = SlackApiError(message="Upload failed", response={"error": "upload_error"})

    event = MagicMock(spec=IncomingNotificationDataBase)
    event.channel_id = "CHANNEL_ID"
    event.thread_id = "1620834875.000400"

    await slack_output_handler.upload_file_to_slack(event, "file_content", "filename.txt", "title")

    assert mock_send_message.call_count == 2  # Initial message and error message
    assert "Error uploading file" in mock_send_message.call_args_list[1][0][2]

@pytest.mark.asyncio
async def test_upload_file_to_slack_empty_content(slack_output_handler, mocker):
    mock_send_message = mocker.patch.object(slack_output_handler, 'send_slack_message', new_callable=AsyncMock)
    mock_client = mocker.patch.object(slack_output_handler.client, 'files_upload_v2', new_callable=MagicMock)

    event = MagicMock(spec=IncomingNotificationDataBase)
    event.channel_id = "CHANNEL_ID"
    event.thread_id = "1620834875.000400"

    await slack_output_handler.upload_file_to_slack(event, "", "filename.txt", "title")

    mock_client.assert_called_once_with(channel="CHANNEL_ID", thread_ts="1620834875.000400", title="title", filename="filename.txt", content="Empty result")
