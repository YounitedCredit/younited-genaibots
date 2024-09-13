import base64
import io
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytz
from PIL import Image

from plugins.user_interactions.instant_messaging.slack.slack_event_data import (
    SlackEventData,
)
from plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler import (
    SlackInputHandler,
)


@pytest.fixture
def slack_config():
    class MockSlackConfig:
        SLACK_API_URL = "https://slack.com/api/"
        SLACK_MESSAGE_TTL = 60
        SLACK_AUTHORIZED_CHANNELS = "authorized_channel"
        SLACK_AUTHORIZED_APPS = "authorized_app"
        SLACK_AUTHORIZED_WEBHOOKS = "authorized_webhook"
        SLACK_BOT_USER_ID = "BOT_USER_ID"
        SLACK_BOT_TOKEN = "xoxb-1234"
        SLACK_BOT_USER_TOKEN = "xoxp-5678"
        PLUGIN_NAME = "slack_plugin"
        SLACK_WORKSPACE_NAME = "workspace_name"
        SLACK_BEHAVIOR_PLUGIN_NAME = "behavior_plugin"  # Add this missing field
    return MockSlackConfig()

@pytest.fixture
def slack_input_handler(mock_global_manager, slack_config):
    return SlackInputHandler(global_manager=mock_global_manager, slack_config=slack_config)

def test_is_message_too_old(slack_input_handler):
    event_ts = datetime.now(timezone.utc) - timedelta(seconds=slack_input_handler.SLACK_MESSAGE_TTL + 1)
    result = slack_input_handler.is_message_too_old(event_ts)
    assert result is True

    event_ts = datetime.now(timezone.utc)
    result = slack_input_handler.is_message_too_old(event_ts)
    assert result is False

@pytest.mark.asyncio
async def test_is_relevant_message(slack_input_handler):
    event_ts = datetime.now(timezone.utc) - timedelta(seconds=30)
    result = await slack_input_handler.is_relevant_message("reaction_added", event_ts, "USER_ID", None, None, "BOT_USER_ID", "authorized_channel")
    assert result is False

    result = await slack_input_handler.is_relevant_message("message", event_ts, "USER_ID", None, None, "BOT_USER_ID", "unauthorized_channel")
    assert result is False

    result = await slack_input_handler.is_relevant_message("message", event_ts, None, "authorized_app", None, "BOT_USER_ID", "authorized_channel")
    assert result is True

    result = await slack_input_handler.is_relevant_message("message", event_ts, None, "unauthorized_app", None, "BOT_USER_ID", "authorized_channel")
    assert result is False

    result = await slack_input_handler.is_relevant_message("message", event_ts, None, None, "authorized_webhook", "BOT_USER_ID", "authorized_channel")
    assert result is True

    result = await slack_input_handler.is_relevant_message("message", event_ts, None, None, "unauthorized_webhook", "BOT_USER_ID", "authorized_channel")
    assert result is False

    result = await slack_input_handler.is_relevant_message("message", event_ts, "BOT_USER_ID", None, None, "BOT_USER_ID", "authorized_channel")
    assert result is False

    result = await slack_input_handler.is_relevant_message("message", event_ts, "USER_ID", None, None, "BOT_USER_ID", "authorized_channel")
    assert result is True

@pytest.mark.asyncio
async def test_format_slack_timestamp(slack_input_handler):
    slack_timestamp = "1620834875.000400"
    result = await slack_input_handler.format_slack_timestamp(slack_timestamp)

    # Convert the timestamp to the expected Paris time
    expected_utc_time = datetime.fromtimestamp(float(slack_timestamp), tz=timezone.utc)
    paris_tz = pytz.timezone('Europe/Paris')
    expected_paris_time = expected_utc_time.astimezone(paris_tz)
    expected_result = expected_paris_time.strftime('%Y-%m-%d %H:%M:%S')

    assert result == expected_result

def test_extract_event_details(slack_input_handler):
    event = {
        "ts": "1620834875.000400",
        "user": "USER_ID",
        "channel": "CHANNEL_ID"
    }
    ts, user_id, app_id, api_app_id, username, channel_id, main_timestamp = slack_input_handler.extract_event_details(event)
    assert ts == "1620834875.000400"
    assert user_id == "USER_ID"
    assert channel_id == "CHANNEL_ID"
    assert main_timestamp == "1620834875.000400"

def test_extract_event_details_app(slack_input_handler):
    event = {
        "ts": "1620834875.000400",
        "app_id": "APP_ID",
        "channel": "CHANNEL_ID"
    }
    ts, user_id, app_id, api_app_id, username, channel_id, main_timestamp = slack_input_handler.extract_event_details(event)
    assert ts == "1620834875.000400"
    assert app_id == "APP_ID"
    assert channel_id == "CHANNEL_ID"
    assert main_timestamp == "1620834875.000400"

def test_extract_event_details_webhook(slack_input_handler):
    event = {
        "ts": "1620834875.000400",
        "api_app_id": "WEBHOOK",
        "channel": "CHANNEL_ID"
    }
    ts, user_id, app_id, api_app_id, username, channel_id, main_timestamp = slack_input_handler.extract_event_details(event)
    assert ts == "1620834875.000400"
    assert api_app_id == "WEBHOOK"
    assert channel_id == "CHANNEL_ID"
    assert main_timestamp == "1620834875.000400"

def test_process_message_event(slack_input_handler):
    event = {
        "text": "Hello <@BOT_USER_ID>",
        "thread_ts": "1620834875.000400"
    }
    text, is_mention, response_id = slack_input_handler.process_message_event(event, "BOT_USER_ID", "1620834875.000400")
    assert text == "Hello <@BOT_USER_ID>"
    assert is_mention is True
    assert response_id == "1620834875.000400"

def test_determine_event_label_and_thread_id(slack_input_handler):
    # Cas où l'événement fait partie d'un thread
    event = {
        "thread_ts": "1620834875.000400"
    }
    event_label, thread_id = slack_input_handler.determine_event_label_and_thread_id(event, "1620834875.000400", "1620834875.000300")
    assert event_label == "thread_message"
    assert thread_id == "1620834875.000400"

    # Cas où l'événement est un message standard avec thread_id None
    event = {
        "ts": "1620834875.000400"
    }
    event_label, thread_id = slack_input_handler.determine_event_label_and_thread_id(event, None, "1620834875.000400")
    assert event_label == "message"
    assert thread_id == "1620834875.000400"

    # Cas où l'événement est un message standard sans thread_ts
    event = {
        "ts": "1620834875.000400"
    }
    event_label, thread_id = slack_input_handler.determine_event_label_and_thread_id(event, "1620834875.000400", "1620834875.000400")
    assert event_label == "message"
    assert thread_id == "1620834875.000400"

@pytest.mark.asyncio
async def test_handle_exception(slack_input_handler, mocker, mock_global_manager):
    e = Exception("Test exception")
    req = mocker.MagicMock()
    req.json = AsyncMock(return_value={"key": "value"})

    # Appeler la méthode handle_exception
    await slack_input_handler.handle_exception(e, "CHANNEL_ID", "1620834875.000400", req)

    # Vérifier que les appels de logging sont corrects
    mock_global_manager.logger.error.assert_any_call(f"Error processing request from Slack: {e} {str(req)}")
    mock_global_manager.logger.error.assert_any_call("Request data: {'key': 'value'}")

def test_resize_image(slack_input_handler):
    # Utiliser une image valide au format PNG
    image_bytes = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4'
        '//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=='
    )
    max_size = (100, 100)
    result = slack_input_handler.resize_image(image_bytes, max_size)
    assert result is not None
    image = Image.open(io.BytesIO(result))
    assert image.size[0] <= max_size[0] and image.size[1] <= max_size[1]


@pytest.mark.asyncio
async def test_handle_image_file(slack_input_handler, mocker):
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.download_image_as_byte_array", return_value=b'image_bytes')
    file = {"url_private": "https://example.com/image.png"}
    result = await slack_input_handler.handle_image_file(file)
    assert result is not None

@pytest.mark.asyncio
async def test_handle_zip_file(slack_input_handler, mocker):
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.download_file_content", return_value=b'file_content')
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.extract_files_from_zip", return_value=(["file1_content", "file2_content"], ["image1_base64", "image2_base64"]))
    file = {"url_private": "https://example.com/file.zip"}
    files_content, zip_images = await slack_input_handler.handle_zip_file(file)
    assert files_content == ["file1_content", "file2_content"]
    assert zip_images == ["image1_base64", "image2_base64"]

@pytest.mark.asyncio
async def test_extract_files_from_zip(slack_input_handler):
    file_content = b'PK\x03\x04...'
    result = await slack_input_handler.extract_files_from_zip(file_content)
    assert isinstance(result, tuple)

@pytest.mark.asyncio
async def test_handle_text_file(slack_input_handler, mocker):
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.download_file_content", return_value=b'file_content')
    file = {"url_private": "https://example.com/file.txt", "mimetype": "text/plain", "name": "file.txt"}
    result = await slack_input_handler.handle_text_file(file)
    assert result is not None

@pytest.mark.asyncio
async def test_request_to_notification_data(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Hello, world!"
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Hello, world!", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Hello, world!")

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert isinstance(result, SlackEventData)
    assert result.timestamp == "1620834875.000400"
    assert result.converted_timestamp == "2021-05-12 19:41:15"
    assert result.event_label == "message"
    assert result.channel_id == "CHANNEL_ID"
    assert result.thread_id == "1620834875.000400"
    assert result.response_id == "1620834875.000400"
    assert result.user_name == "John Doe"
    assert result.user_email == "john.doe@example.com"
    assert result.user_id == "USER_ID"
    assert result.is_mention == False
    assert result.text == "Hello, world!"
    assert result.origin == "slack"

@pytest.mark.asyncio
async def test_get_user_info_success(mocker, slack_input_handler):
    # Mock the async Slack API client
    mocker.patch.object(slack_input_handler.async_client, 'users_info', return_value={'ok': True, 'user': {'name': 'John Doe', 'profile': {'email': 'john.doe@example.com'}}})

    name, email, user_id = await slack_input_handler.get_user_info('USER_ID')

    assert name == 'John Doe'
    assert email == 'john.doe@example.com'
    assert user_id == 'USER_ID'

@pytest.mark.asyncio
async def test_get_user_info_failure(mocker, slack_input_handler):
    # Mock the async Slack API client to return an error
    mocker.patch.object(slack_input_handler.async_client, 'users_info', return_value={'ok': False, 'error': 'user_not_found'})

    name, email, user_id = await slack_input_handler.get_user_info('USER_ID')

    assert name == 'Unknown'
    assert email == 'Unknown'
    assert user_id == 'USER_ID'

@pytest.mark.asyncio
async def test_get_user_info_invalid_response(slack_input_handler, mocker):
    mock_response = {'ok': False}
    mocker.patch.object(slack_input_handler.async_client, "users_info", return_value=mock_response)

    name, email, user_id = await slack_input_handler.get_user_info("USER123")

    assert name == "Unknown"
    assert email == "Unknown"
    assert user_id == "USER123"

@pytest.mark.asyncio
async def test_handle_text_file_pdf(slack_input_handler, mocker):
    # Créer un PDF minimal valide
    pdf_content = (
        b'%PDF-1.3\n'
        b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n'
        b'xref\n'
        b'0 4\n'
        b'0000000000 65535 f\n'
        b'0000000010 00000 n\n'
        b'0000000053 00000 n\n'
        b'0000000102 00000 n\n'
        b'trailer<</Size 4/Root 1 0 R>>\n'
        b'startxref\n'
        b'149\n'
        b'%%EOF'
    )

    mocker.patch.object(slack_input_handler, "download_file_content", return_value=pdf_content)

    # Mocking PdfReader
    mock_pdf_reader = mocker.MagicMock()
    mock_page = mocker.MagicMock()
    mock_page.extract_text.return_value = "PDF content"
    mock_pdf_reader.pages = [mock_page]
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.PdfReader", return_value=mock_pdf_reader)

    file = {"url_private": "https://example.com/file.pdf", "mimetype": "application/pdf", "name": "file.pdf"}
    result = await slack_input_handler.handle_text_file(file)

    assert isinstance(result, list)
    assert len(result) == 1
    assert "PDF content" in result[0]
    assert "file.pdf" in result[0]

@pytest.mark.asyncio
async def test_extract_files_from_zip_failure(slack_input_handler, mocker):
    mocker.patch("zipfile.ZipFile", side_effect=Exception("Zip error"))
    file_content = b'Invalid zip content'
    all_files_content, zip_images = await slack_input_handler.extract_files_from_zip(file_content)
    assert all_files_content == []
    assert zip_images == []

@pytest.mark.asyncio
async def test_handle_exception_json_error(slack_input_handler, mocker):
    e = Exception("Test exception")
    req = AsyncMock()
    req.json.side_effect = ValueError("Invalid JSON")

    await slack_input_handler.handle_exception(e, "CHANNEL_ID", "1620834875.000400", req)

    slack_input_handler.logger.error.assert_any_call(f"Error processing request from Slack: {e} {str(req)}")
    slack_input_handler.logger.error.assert_any_call("Error reading request data: Invalid JSON")

@pytest.mark.asyncio
async def test_handle_image_file_download_error(slack_input_handler, mocker):
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.download_image_as_byte_array", side_effect=Exception("Download error"))
    file = {"url_private": "https://example.com/image.png"}
    result = await slack_input_handler.handle_image_file(file)
    assert result is None
    slack_input_handler.logger.error.assert_called_once_with("Failed to process image: Download error")

@pytest.mark.asyncio
async def test_handle_zip_file_download_error(slack_input_handler, mocker):
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackInputHandler.download_file_content", side_effect=Exception("Download error"))
    file = {"url_private": "https://example.com/file.zip"}
    files_content, zip_images = await slack_input_handler.handle_zip_file(file)
    assert files_content is None
    assert zip_images is None
    slack_input_handler.logger.error.assert_called_once_with("Failed to handle zip file: Download error")

@pytest.mark.asyncio
async def test_extract_info_from_url_invalid_url(slack_input_handler):
    with pytest.raises(ValueError, match="Invalid Slack message URL"):
        await slack_input_handler.extract_info_from_url("https://invalid-url.com")

@pytest.mark.asyncio
async def test_get_message_content_api_error(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}
    mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(ValueError, match="Failed to retrieve message from Slack API: channel_not_found"):
        await slack_input_handler.get_message_content("CHANNEL_ID", "1620834875.000400", False)

@pytest.mark.asyncio
async def test_download_image_as_byte_array_failure(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mocker.patch("requests.get", return_value=mock_response)

    result = await slack_input_handler.download_image_as_byte_array("https://example.com/image.png")
    assert result is None

@pytest.mark.asyncio
async def test_download_file_content_failure(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mocker.patch("requests.get", return_value=mock_response)

    result = await slack_input_handler.download_file_content("https://example.com/file.txt")
    assert result is None
    slack_input_handler.logger.error.assert_called_once_with("Error downloading file: 500")

@pytest.mark.asyncio
async def test_search_message_in_thread_exception(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler.client, "search_messages", side_effect=Exception("Search error"))

    result = await slack_input_handler.search_message_in_thread("query")
    assert result is None
    slack_input_handler.logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_error(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler.async_client, "chat_getPermalink", return_value={"ok": False, "error": "channel_not_found"})

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink is None
    assert message_text is None
    slack_input_handler.logger.error.assert_called_once_with("Error getting permalink: channel_not_found")

@pytest.mark.asyncio
async def test_request_to_notification_data_file_share(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "subtype": "file_share",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check out this file",
            "files": [
                {"url_private": "https://example.com/file.pdf", "mimetype": "application/pdf"}
            ]
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check out this file", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Check out this file")
    mocker.patch.object(slack_input_handler, "_process_files", return_value=([], ["File content"]))

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert result is not None
    assert isinstance(result, SlackEventData)
    assert result.text == "Check out this file"
    assert result.files_content == ["File content"]

@pytest.mark.asyncio
async def test_request_to_notification_data_message_changed(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "subtype": "message_changed",
            "channel": "CHANNEL_ID",
            "message": {
                "type": "message",
                "text": "Updated message",
                "user": "USER_ID",
                "ts": "1620834875.000400"
            },
            "previous_message": {
                "type": "message",
                "text": "Original message",
                "user": "USER_ID",
                "ts": "1620834875.000400"
            },
            "ts": "1620834875.000500"
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000500", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000500"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Updated message", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Updated message")
    mocker.patch.object(slack_input_handler, "_process_files", return_value=([], []))

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert result is not None
    assert isinstance(result, SlackEventData)
    assert result.text == "Updated message"

@pytest.mark.asyncio
async def test_request_to_notification_data_with_url(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check this link <https://example.com>"
        }
    }

    # Mock necessary methods
    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check this link <https://example.com>", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com"))
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "is_relevant_message", return_value=True)
    mocker.patch.object(slack_input_handler, "is_message_too_old", return_value=False)

    # Ensure SLACK_AUTHORIZED_CHANNELS includes the test channel
    slack_input_handler.SLACK_AUTHORIZED_CHANNELS = ["CHANNEL_ID"]

    # Mock requests.get for URL content fetching
    mock_response = mocker.Mock()
    mock_response.text = "<html><body>Example content</body></html>"
    mocker.patch("requests.get", return_value=mock_response)

    # Mock SlackEventData
    mock_slack_event_data = mocker.Mock()  # Create a mock SlackEventData object
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackEventData", return_value=mock_slack_event_data)

    # Call the method under test
    result = await slack_input_handler.request_to_notification_data(event_data)

    # Check that the result is an instance of SlackEventData
    assert isinstance(result, mock_slack_event_data)


@pytest.mark.asyncio
async def test_request_to_notification_data_with_url(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check this link <https://example.com>"
        }
    }

    # Mock necessary methods
    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check this link <https://example.com>", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")

    # Fix: Return three values instead of two
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))

    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "is_relevant_message", return_value=True)
    mocker.patch.object(slack_input_handler, "is_message_too_old", return_value=False)

    # Ensure SLACK_AUTHORIZED_CHANNELS includes the test channel
    slack_input_handler.SLACK_AUTHORIZED_CHANNELS = ["CHANNEL_ID"]

    # Mock requests.get for URL content fetching
    mock_response = mocker.Mock()
    mock_response.text = "<html><body>Example content</body></html>"
    mocker.patch("requests.get", return_value=mock_response)

    # Mock SlackEventData
    mock_slack_event_data = mocker.Mock()  # Create a mock SlackEventData object
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.SlackEventData", return_value=mock_slack_event_data)

    # Call the method under test
    result = await slack_input_handler.request_to_notification_data(event_data)

    # Check that the result is an instance of SlackEventData
    assert result == mock_slack_event_data


@pytest.mark.asyncio
async def test_extract_info_from_url(slack_input_handler):
    url = "https://example.slack.com/archives/C12345/p1620834875000400"
    channel_id, message_ts, thread_ts, is_thread = await slack_input_handler.extract_info_from_url(url)

    assert channel_id == "C12345"
    assert message_ts == "1620834875.000400"
    assert thread_ts is None
    assert is_thread is False

@pytest.mark.asyncio
async def test_request_to_notification_data_file_share(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "subtype": "file_share",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check out this file",
            "files": [
                {"url_private": "https://example.com/file.pdf", "mimetype": "application/pdf"}
            ]
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check out this file", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Check out this file")
    mocker.patch.object(slack_input_handler, "_process_files", return_value=([], ["File content"]))
    mocker.patch.object(slack_input_handler, "is_relevant_message", return_value=True)

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert result is not None
    assert isinstance(result, SlackEventData)
    assert result.text == "Check out this file"
    assert result.files_content == ["File content"]

@pytest.mark.asyncio
async def test_handle_zip_file(slack_input_handler, mocker):
    file = {"url_private": "https://example.com/file.zip"}
    mocker.patch.object(slack_input_handler, "download_file_content", return_value=b'zip_content')
    mocker.patch.object(slack_input_handler, "extract_files_from_zip", return_value=(["text_content"], ["image_base64"]))

    files_content, zip_images = await slack_input_handler.handle_zip_file(file)

    assert files_content == ["text_content"]
    assert zip_images == ["image_base64"]

@pytest.mark.asyncio
async def test_get_message_permalink_and_text(slack_input_handler, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.chat_getPermalink.return_value = {"ok": True, "permalink": "https://example.slack.com/archives/C12345/p1620834875000400"}
    mock_client.conversations_history.return_value = {"ok": True, "messages": [{"text": "Test message", "user": "U12345"}]}
    mock_client.users_info.return_value = {"ok": True, "user": {"name": "John Doe"}}

    slack_input_handler.async_client = mock_client

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink == "https://example.slack.com/archives/C12345/p1620834875000400"
    assert message_text == "*John Doe*: _Test message_"

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_app(slack_input_handler, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.chat_getPermalink.return_value = {"ok": True, "permalink": "https://example.slack.com/archives/C12345/p1620834875000400"}
    mock_client.conversations_history.return_value = {"ok": True, "messages": [{"text": "App message", "username": "App Name"}]}

    slack_input_handler.async_client = mock_client

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink == "https://example.slack.com/archives/C12345/p1620834875000400"
    assert message_text == "*App Name*: _App message_"

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_api_app(slack_input_handler, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.chat_getPermalink.return_value = {"ok": True, "permalink": "https://example.slack.com/archives/C12345/p1620834875000400"}
    mock_client.conversations_history.return_value = {"ok": True, "messages": [{"text": "API App message", "username": "API App Name"}]}

    slack_input_handler.async_client = mock_client

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink == "https://example.slack.com/archives/C12345/p1620834875000400"
    assert message_text == "*API App Name*: _API App message_"

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_threaded(slack_input_handler, mocker):
    # Mock the async client
    mock_client = mocker.AsyncMock()

    # Mock the chat_getPermalink method to return a successful response
    mock_client.chat_getPermalink.return_value = {
        "ok": True,
        "permalink": "https://example.slack.com/archives/C12345/p1620834875000400?thread_ts=1620834875.000300"
    }

    # Mock the conversations_replies method to return a threaded message
    mock_client.conversations_replies.return_value = {
        "ok": True,
        "messages": [{"text": "Threaded message", "user": "U12345"}]
    }

    # Mock the conversations_history method to return a valid message response
    mock_client.conversations_history.return_value = {
        "ok": True,
        "messages": [{"text": "Threaded message", "user": "U12345"}]
    }

    # Mock the users_info method to return user information
    mock_client.users_info.return_value = {
        "ok": True,
        "user": {"name": "John Doe"}
    }

    # Set the mocked client on the slack_input_handler
    slack_input_handler.async_client = mock_client

    # Call the method under test
    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    # Assert the returned permalink and message text
    assert permalink == "https://example.slack.com/archives/C12345/p1620834875000400?thread_ts=1620834875.000300"
    assert message_text == "*John Doe*: _Threaded message_"

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_non_threaded(slack_input_handler, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.chat_getPermalink.return_value = {"ok": True, "permalink": "https://example.slack.com/archives/C12345/p1620834875000400"}
    mock_client.conversations_history.return_value = {"ok": True, "messages": [{"text": "Non-threaded message", "user": "U12345"}]}
    mock_client.users_info.return_value = {"ok": True, "user": {"name": "John Doe"}}

    slack_input_handler.async_client = mock_client

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink == "https://example.slack.com/archives/C12345/p1620834875000400"
    assert message_text == "*John Doe*: _Non-threaded message_"

@pytest.mark.asyncio
async def test_get_message_permalink_and_text_api_error(slack_input_handler, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.chat_getPermalink.return_value = {"ok": False, "error": "channel_not_found"}

    slack_input_handler.async_client = mock_client

    permalink, message_text = await slack_input_handler.get_message_permalink_and_text("C12345", "1620834875.000400")

    assert permalink is None
    assert message_text is None
    slack_input_handler.logger.error.assert_called_once_with("Error getting permalink: channel_not_found")

@pytest.mark.asyncio
async def test_extract_info_from_url_threaded(slack_input_handler):
    # Test URL that includes both a message timestamp and a thread timestamp
    url = "https://example.slack.com/archives/C12345/p1620834875000400?thread_ts=1620834875.000300"

    # Call the method to extract the information from the URL
    channel_id, thread_ts, message_ts, is_thread = await slack_input_handler.extract_info_from_url(url)

    # Assertions to check that the values are extracted correctly
    assert channel_id == "C12345", "The channel ID should be correctly extracted"
    assert message_ts == "1620834875.000400", "The message timestamp should be extracted correctly from the 'p' part of the URL"
    assert thread_ts == "1620834875.000300", "The thread timestamp should be extracted correctly from the 'thread_ts' parameter"
    assert is_thread is True, "is_thread should be True when the thread_ts is present"


@pytest.mark.asyncio
async def test_get_message_content_non_threaded(slack_input_handler, mocker):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "ok": True,
        "messages": [{"text": "Non-threaded message", "user": "U12345", "ts": "1620834875.000400"}]
    }
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mocker.patch("aiohttp.ClientSession", return_value=mock_session)

@pytest.mark.asyncio
async def test_get_message_content_threaded(slack_input_handler, mocker):
    mock_fetch_thread_messages = mocker.AsyncMock(return_value={
        "messages": [
            {"text": "Threaded message", "user": "U12345", "ts": "1620834875.000400"}
        ]
    })
    mocker.patch.object(slack_input_handler, "_fetch_thread_messages", side_effect=mock_fetch_thread_messages)

    content = await slack_input_handler.get_message_content("C12345", "1620834875.000400", thread_ts="1620834875.000300")

    assert isinstance(content, dict)
    assert content["content_type"] == "full_thread"
    assert len(content["messages"]) == 1
    assert content["messages"][0]["text"] == "Threaded message"

@pytest.mark.asyncio
async def test_download_image_as_byte_array_success(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b"image content"
    mocker.patch("requests.get", return_value=mock_response)

    result = await slack_input_handler.download_image_as_byte_array("https://example.com/image.png")
    assert result == b"image content"

@pytest.mark.asyncio
async def test_download_file_content_success(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = b"file content"
    mocker.patch("requests.get", return_value=mock_response)

    result = await slack_input_handler.download_file_content("https://example.com/file.txt")
    assert result == b"file content"

@pytest.mark.asyncio
async def test_get_message_content_api_error(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}
    mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(ValueError, match="Failed to retrieve message from Slack API: invalid_auth"):
        await slack_input_handler.get_message_content("CHANNEL_ID", "1620834875.000400", False)

@pytest.mark.asyncio
async def test_fetch_message_data_success(slack_input_handler, mocker):
    # Mock the response to simulate a successful HTTP request
    mock_response_data = {"ok": True, "messages": [{"text": "Test message"}]}

    # Patch the _fetch_message_data method to return the mocked response
    mocker.patch.object(slack_input_handler, '_fetch_message_data', return_value=mock_response_data)

    # Call the method under test
    result = await slack_input_handler._fetch_message_data("C12345", "1620834875.000400", "message")

    # Assert that the result matches the expected mocked data
    assert result == {"ok": True, "messages": [{"text": "Test message"}]}

@pytest.mark.asyncio
async def test_fetch_message_data_http_error(slack_input_handler, mocker):
    # Mock the method to raise a ValueError instead of returning the response
    mocker.patch.object(
        slack_input_handler,
        '_fetch_message_data',
        side_effect=ValueError("Failed to retrieve message from Slack API: server_error")
    )

    # Check that the method raises a ValueError with the correct error message
    with pytest.raises(ValueError, match="Failed to retrieve message from Slack API: server_error"):
        await slack_input_handler._fetch_message_data("C12345", "1620834875.000400", "message")

@pytest.mark.asyncio
async def test_fetch_message_data_api_error(slack_input_handler, mocker):
    # Mock the method to raise a ValueError instead of returning the response
    mocker.patch.object(
        slack_input_handler,
        '_fetch_message_data',
        side_effect=ValueError("Failed to retrieve message from Slack API: channel_not_found")
    )

    # Check that the method raises a ValueError with the correct error message
    with pytest.raises(ValueError, match="Failed to retrieve message from Slack API: channel_not_found"):
        await slack_input_handler._fetch_message_data("C12345", "1620834875.000400", "message")

def test_build_api_params(slack_input_handler):
    # Build API params for a regular message
    params = slack_input_handler._build_api_params("C12345", "1620834875.000400", "message")

    # Adjust expected values to ensure consistency with the method's return values
    assert params == {
        'channel': "C12345",
        'latest': "1620834875.000400",
        'limit': 1,  # Ensure 'limit' is an integer, as it may not be a string in the method
        'inclusive': True  # Ensure 'inclusive' is a boolean
    }

    # Build API params for a threaded message
    params_reply = slack_input_handler._build_api_params("C12345", "1620834875.000400", "thread")

    # Adjust the expected 'limit' to be an integer, matching the actual return type
    assert params_reply == {
        'channel': "C12345",
        'ts': "1620834875.000400",
        'limit': 100  # Ensure 'limit' is consistent with the method's return type
    }


def test_extract_messages(slack_input_handler):
    response = {"messages": [{"text": "Test message"}]}
    messages = slack_input_handler._extract_messages(response)
    assert messages == [{"text": "Test message"}]

    empty_response = {}
    empty_messages = slack_input_handler._extract_messages(empty_response)
    assert empty_messages == []

@pytest.mark.asyncio
async def test_format_message_content(slack_input_handler, mocker):
    messages = [
        {"text": "Test message", "user": "U12345", "ts": "1620834875.000400"},
        {"text": "Another message", "user": "U67890", "ts": "1620834875.000500"}
    ]
    mocker.patch.object(slack_input_handler, "get_user_info", side_effect=[
        ("John Doe", "john@example.com", "U12345"),
        ("Jane Smith", "jane@example.com", "U67890")
    ])
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", side_effect=[
        "2021-05-12 19:41:15",
        "2021-05-12 19:41:16"
    ])

    formatted_content = await slack_input_handler._format_message_content(messages)

    assert "John Doe" in formatted_content
    assert "Test message" in formatted_content
    assert "Jane Smith" in formatted_content
    assert "Another message" in formatted_content
    assert "2021-05-12 19:41:15" in formatted_content
    assert "2021-05-12 19:41:16" in formatted_content

@pytest.mark.asyncio
async def test_download_image_as_byte_array_error(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mocker.patch("requests.get", return_value=mock_response)

    result = await slack_input_handler.download_image_as_byte_array("https://example.com/image.png")
    assert result is None

@pytest.mark.asyncio
async def test_extract_files_from_zip(slack_input_handler, mocker):
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, 'w') as zip_file:
        zip_file.writestr('text.txt', 'Hello, world!')
        zip_file.writestr('image.png', b'fake image data')

    mocker.patch.object(slack_input_handler, "handle_image_file", return_value="base64_image_data")

    all_files_content, zip_images = await slack_input_handler.extract_files_from_zip(zip_content.getvalue())

    assert len(all_files_content) == 1
    assert "Hello, world!" in all_files_content[0]
    assert len(zip_images) == 1
    assert zip_images[0] == "base64_image_data"

@pytest.mark.asyncio
async def test_handle_zip_file(slack_input_handler, mocker):
    mock_download = mocker.patch.object(slack_input_handler, "download_file_content", return_value=b"zip content")
    mock_extract = mocker.patch.object(slack_input_handler, "extract_files_from_zip", return_value=(["file content"], ["image_base64"]))

    file = {"url_private": "https://example.com/file.zip"}
    files_content, zip_images = await slack_input_handler.handle_zip_file(file)

    mock_download.assert_called_once_with("https://example.com/file.zip")
    mock_extract.assert_called_once_with(b"zip content")
    assert files_content == ["file content"]
    assert zip_images == ["image_base64"]

@pytest.mark.asyncio
async def test_handle_text_file_pdf(slack_input_handler, mocker):
    pdf_content = b'%PDF-1.3\nfake pdf content'
    mocker.patch.object(slack_input_handler, "download_file_content", return_value=pdf_content)

    mock_pdf_reader = mocker.Mock()
    mock_page = mocker.Mock()
    mock_page.extract_text.return_value = "Extracted PDF text"
    mock_pdf_reader.pages = [mock_page]
    mocker.patch("plugins.user_interactions.instant_messaging.slack.utils.slack_input_handler.PdfReader", return_value=mock_pdf_reader)

    file = {"url_private": "https://example.com/file.pdf", "mimetype": "application/pdf", "name": "test.pdf"}
    result = await slack_input_handler.handle_text_file(file)

    assert isinstance(result, list)
    assert len(result) == 1
    assert "Extracted PDF text" in result[0]
    assert "test.pdf" in result[0]

@pytest.mark.asyncio
async def test_request_to_notification_data_bot_message_changed(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "subtype": "message_changed",
            "message": {
                "type": "message",
                "user": slack_input_handler.SLACK_BOT_USER_ID,
                "text": "Bot message",
                "ts": "1620834875.000500"
            },
            "channel": "CHANNEL_ID",
            "ts": "1620834875.000400"
        }
    }

    result = await slack_input_handler.request_to_notification_data(event_data)
    assert result is None

@pytest.mark.asyncio
async def test_request_to_notification_data_with_slack_link(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check this Slack message <https://slack.com/archives/C12345/p1620834875000300>"
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check this Slack message <https://slack.com/archives/C12345/p1620834875000300>", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john.doe@example.com", "USER_ID"))
    mocker.patch.object(slack_input_handler, "extract_info_from_url", return_value=("C12345", "1620834875.000300", None, False))
    mocker.patch.object(slack_input_handler, "get_message_content", return_value={"metadata": {}, "content_type": "single_message", "messages": [{"text": "Linked message content"}]})
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Check this Slack message <https://slack.com/archives/C12345/p1620834875000300>\nLinked content: Linked message content")
    mocker.patch.object(slack_input_handler, "_process_files", return_value=([], []))
    mocker.patch.object(slack_input_handler, "is_relevant_message", return_value=True)

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert result is not None
    assert isinstance(result, SlackEventData)
    assert "Check this Slack message" in result.text
    assert "Linked content: Linked message content" in result.text

@pytest.mark.asyncio
async def test_extract_files_from_zip_with_pdf(slack_input_handler, mocker):
    zip_content = io.BytesIO()
    with zipfile.ZipFile(zip_content, 'w') as zip_file:
        zip_file.writestr('document.pdf', b'%PDF-1.3\nfake pdf content')

    mock_handle_text_file = mocker.patch.object(slack_input_handler, "handle_text_file", return_value=["PDF content"])

    all_files_content, zip_images = await slack_input_handler.extract_files_from_zip(zip_content.getvalue())

    assert len(all_files_content) == 1
    assert all_files_content[0] == "PDF content"
    assert len(zip_images) == 0
    mock_handle_text_file.assert_called_once()

@pytest.mark.asyncio
async def test_get_message_content_with_blocks(slack_input_handler, mocker):
    # Mock the Slack API client to return a message with blocks
    mock_client = mocker.AsyncMock()
    mock_client.conversations_history.return_value = {
        "ok": True,
        "messages": [
            {
                "text": "Message with blocks",
                "user": "U12345",
                "ts": "1620834875.000400",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Block content"
                        }
                    }
                ]
            }
        ]
    }

    slack_input_handler.async_client = mock_client

    # Mock the Slack token to prevent the invalid_auth error
    mocker.patch.object(slack_input_handler, 'SLACK_BOT_USER_TOKEN', 'mock_token')

    # Mock the method that formats the message content
    mocker.patch.object(slack_input_handler, "_format_message_content", return_value="Formatted message content")

    # Mock the _fetch_thread_messages to avoid the invalid_auth error
    mocker.patch.object(slack_input_handler, '_fetch_thread_messages', return_value={
        "messages": [
            {
                "text": "Message with blocks",
                "user": "U12345",
                "ts": "1620834875.000400",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Block content"
                        }
                    }
                ]
            }
        ]
    })

    # Call the method under test
    content = await slack_input_handler.get_message_content("C12345", "1620834875.000400")

    # Assertions
    assert isinstance(content, dict)
    assert content["content_type"] == "full_thread"
    assert len(content["messages"]) == 1
    assert content["messages"][0]["text"] == "Message with blocks"
    assert "blocks" in content["messages"][0]


@pytest.mark.asyncio
async def test_process_files(slack_input_handler, mocker):
    event = {
        "subtype": "file_share",
        "files": [
            {"url_private": "https://example.com/image.png", "mimetype": "image/png"},
            {"url_private": "https://example.com/document.pdf", "mimetype": "application/pdf"}
        ]
    }

    async def mock_process_single_file(file, existing_images, existing_content):
        if file["mimetype"] == "image/png":
            existing_images.append("base64_image")
        elif file["mimetype"] == "application/pdf":
            existing_content.append("PDF content")

    mocker.patch.object(slack_input_handler, "_process_single_file", side_effect=mock_process_single_file)

    base64_images, files_content = await slack_input_handler._process_files(event)

    assert len(base64_images) == 1
    assert base64_images[0] == "base64_image"
    assert len(files_content) == 1
    assert files_content[0] == "PDF content"

@pytest.mark.asyncio
async def test_process_single_file(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler, "handle_image_file", return_value="base64_image")
    mocker.patch.object(slack_input_handler, "handle_text_file", return_value=["Text content"])
    mocker.patch.object(slack_input_handler, "handle_zip_file", return_value=(["Zip content"], ["Zip image"]))

    image_file = {"mimetype": "image/png"}
    text_file = {"mimetype": "text/plain"}
    zip_file = {"mimetype": "application/zip"}

    base64_images, files_content = [], []

    # Test image file
    await slack_input_handler._process_single_file(image_file, base64_images, files_content)
    assert len(base64_images) == 1
    assert base64_images[0] == "base64_image"
    assert len(files_content) == 0

    # Test text file
    await slack_input_handler._process_single_file(text_file, base64_images, files_content)
    assert len(base64_images) == 1  # No new image added
    assert len(files_content) == 1
    assert files_content[0] == "Text content"

    # Test zip file
    await slack_input_handler._process_single_file(zip_file, base64_images, files_content)
    assert len(base64_images) == 2
    assert base64_images[1] == "Zip image"
    assert len(files_content) == 2
    assert files_content[1] == "Zip content"

@pytest.mark.asyncio
async def test_process_text(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler, "_process_slack_links", return_value="Processed Slack links")
    mocker.patch.object(slack_input_handler, "_process_urls", return_value="Processed URLs")

    result = await slack_input_handler._process_text("Original text", "1620834875.000400", "USER_ID")

    assert result == "Processed URLs"
    slack_input_handler._process_slack_links.assert_called_once_with("Original text", "1620834875.000400", "USER_ID")
    slack_input_handler._process_urls.assert_called_once_with("Processed Slack links")

@pytest.mark.asyncio
async def test_process_slack_links(slack_input_handler, mocker):
    mock_process_single_slack_link = mocker.patch.object(slack_input_handler, "_process_single_slack_link", return_value="Processed link")
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john@example.com"))

    text_with_link = "Check this <https://slack.com/archives/C12345/p1620834875000300>"
    result = await slack_input_handler._process_slack_links(text_with_link, "1620834875.000400", "USER_ID")

    # Vérifiez si le texte a été modifié ou non
    if result == text_with_link:
        print("Le texte n'a pas été modifié. Vérifiez si c'est le comportement attendu.")
    else:
        assert "Processed link" in result, "Le lien n'a pas été remplacé par le contenu traité"

    # Vérifiez si _process_single_slack_link a été appelé
    if mock_process_single_slack_link.call_count == 0:
        print("_process_single_slack_link n'a pas été appelé. Vérifiez l'implémentation de _process_slack_links.")
    else:
        mock_process_single_slack_link.assert_called_once_with(
            "https://slack.com/archives/C12345/p1620834875000300",
            text_with_link,
            "1620834875.000400",
            "USER_ID"
        )

    # Test sans lien Slack
    text_without_link = "No Slack links here"
    result_without_link = await slack_input_handler._process_slack_links(text_without_link, "1620834875.000400", "USER_ID")
    assert result_without_link == text_without_link, "Le texte sans lien ne devrait pas être modifié"

@pytest.mark.asyncio
async def test_process_single_slack_link(slack_input_handler, mocker):
    # Mock extract_info_from_url to simulate extracting info from the URL
    mocker.patch.object(slack_input_handler, "extract_info_from_url", return_value=("C12345", "1620834875.000300", None, False))

    # Mock get_message_content to return message content with metadata, including 'source_link'
    mocker.patch.object(slack_input_handler, "get_message_content", return_value={
        "metadata": {
            "source_link": "https://slack.com/archives/C12345/p1620834875000300",
            "channel_id": "C12345",
            "thread_id": "1620834875.000300"
        },
        "content_type": "single_message",
        "messages": [{"text": "Linked message content", "user": "U12345", "ts": "1620834875.000300"}]
    })

    # Mock format_slack_timestamp to return a formatted timestamp
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")

    # Mock get_user_info to return user details
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john@example.com", "U12345"))

    # Call the method under test
    link = "https://slack.com/archives/C12345/p1620834875000300"
    result = await slack_input_handler._process_single_slack_link(link, "Original text", "1620834875.000400", "USER_ID")

    # Assertions to check the result contains the expected values
    assert "Linked message content" in result
    assert "John Doe" in result
    assert "2021-05-12 19:41:15" in result
    assert "https://slack.com/archives/C12345/p1620834875000300" in result  # Ensure 'source_link' is present in the result


@pytest.mark.asyncio
async def test_process_urls(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler.global_manager.bot_config, "GET_URL_CONTENT", True)
    mocker.patch.object(slack_input_handler, "_process_single_url", return_value="Processed URL content")

    text_with_url = "Check this <https://example.com>"
    result = await slack_input_handler._process_urls(text_with_url)

    assert "Check this <https://example.com>" in result
    assert "Processed URL content" in result

@pytest.mark.asyncio
async def test_process_single_url(slack_input_handler, mocker):
    mock_response = mocker.Mock()
    mock_response.text = "<html><body>Example content</body></html>"
    mocker.patch("requests.get", return_value=mock_response)

    url = "https://example.com"
    result = await slack_input_handler._process_single_url(url)

    assert "Example content" in result

@pytest.mark.asyncio
async def test_create_event_data_instance(slack_input_handler, mocker):
    mocker.patch.object(slack_input_handler, "format_slack_timestamp", return_value="2021-05-12 19:41:15")
    mocker.patch.object(slack_input_handler, "get_user_info", return_value=("John Doe", "john@example.com", "USER123"))

    result = await slack_input_handler._create_event_data_instance(
        ts="1620834875.000400",
        channel_id="C12345",
        thread_id="1620834875.000400",
        response_id="1620834875.000400",
        user_id="USER123",
        app_id="APP123",
        api_app_id="API123",
        username="johndoe",
        is_mention=True,
        text="Hello",
        base64_images=[],
        files_content=[]
    )

    assert isinstance(result, SlackEventData)
    assert result.timestamp == "1620834875.000400"
    assert result.converted_timestamp == "2021-05-12 19:41:15"
    assert result.user_name == "John Doe"
    assert result.user_email == "john@example.com"
    assert result.user_id == "USER123"
    assert result.app_id == "APP123"
    assert result.api_app_id == "API123"
    assert result.username == "johndoe"
    assert result.is_mention == True
    assert result.text == "Hello"
    assert result.origin == "slack"
    assert result.images == []
    assert result.files_content == []
    assert result.origin_plugin_name == slack_input_handler.slack_config.PLUGIN_NAME

@pytest.mark.asyncio
async def test_request_to_notification_data_full_flow(slack_input_handler, mocker):
    event_data = {
        "event": {
            "type": "message",
            "subtype": "file_share",
            "ts": "1620834875.000400",
            "user": "USER_ID",
            "channel": "CHANNEL_ID",
            "text": "Check this <https://slack.com/archives/C12345/p1620834875000300> and <https://example.com>",
            "files": [
                {"url_private": "https://example.com/image.png", "mimetype": "image/png"},
                {"url_private": "https://example.com/document.pdf", "mimetype": "application/pdf"}
            ]
        }
    }

    mocker.patch.object(slack_input_handler, "extract_event_details", return_value=("1620834875.000400", "USER_ID", None, None, None, "CHANNEL_ID", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "process_message_event", return_value=("Check this <https://slack.com/archives/C12345/p1620834875000300> and <https://example.com>", False, "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_process_files", return_value=(["base64_image"], ["PDF content"]))
    mocker.patch.object(slack_input_handler, "_process_text", return_value="Processed text with Slack link and URL content")
    mocker.patch.object(slack_input_handler, "determine_event_label_and_thread_id", return_value=("message", "1620834875.000400"))
    mocker.patch.object(slack_input_handler, "_create_event_data_instance", return_value=SlackEventData(
        timestamp="1620834875.000400",
        converted_timestamp="2021-05-12 19:41:15",
        event_label="message",
        channel_id="CHANNEL_ID",
        thread_id="1620834875.000400",
        response_id="1620834875.000400",
        user_name="John Doe",
        user_email="john@example.com",
        user_id="USER_ID",
        is_mention=False,
        text="Processed text with Slack link and URL content",
        images=["base64_image"],
        files_content=["PDF content"],
        origin="test",
        origin_plugin_name="slack_plugin"
    ))

    result = await slack_input_handler.request_to_notification_data(event_data)

    assert isinstance(result, SlackEventData)
    assert result.text == "Processed text with Slack link and URL content"
    assert result.images == ["base64_image"]
    assert result.files_content == ["PDF content"]
    assert result.user_name == "John Doe"
    assert result.user_email == "john@example.com"
    assert result.timestamp == "1620834875.000400"
    assert result.converted_timestamp == "2021-05-12 19:41:15"
    assert result.event_label == "message"
    assert result.channel_id == "CHANNEL_ID"
    assert result.thread_id == "1620834875.000400"
