from unittest.mock import AsyncMock, MagicMock

import pytest
from slack_sdk.errors import SlackApiError

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.user_interactions.instant_messaging.slack.utils.slack_output_handler import (
    SlackOutputHandler,
)


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
async def test_send_slack_message(slack_output_handler, mocker):
    mock_post = mocker.patch("requests.post", return_value=MagicMock(status_code=200))
    response = await slack_output_handler.send_slack_message("CHANNEL_ID", "1620834875.000400", "Hello World")
    assert response.status_code == 200
    mock_post.assert_called_once()

def test_format_slack_message(slack_output_handler):
    blocks = slack_output_handler.format_slack_message("Title", "Message", MessageType.TEXT)
    assert blocks == [{"type": "section", "text": {"type": "mrkdwn", "text": "Message"}}]

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
async def test_send_slack_message_types(slack_output_handler, mocker, message_type):
    mock_post = mocker.patch("requests.post", return_value=MagicMock(status_code=200))
    await slack_output_handler.send_slack_message("CHANNEL_ID", "1620834875.000400", "Message", message_type, "Title")
    mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_send_slack_message_file_type(slack_output_handler, mocker):
    mock_post = mocker.patch("requests.post", return_value=MagicMock(status_code=200))
    await slack_output_handler.send_slack_message("CHANNEL_ID", "1620834875.000400", "Message", MessageType.FILE, "Title")
    mock_post.assert_called_once()

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
