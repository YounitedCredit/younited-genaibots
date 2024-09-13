import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botbuilder.schema import (
    Activity,
    Attachment,
    ChannelAccount,
    ConversationAccount,
    Entity,
)
from fastapi import Request

from plugins.user_interactions.instant_messaging.teams.teams import (
    TeamsConfig,
    TeamsPlugin,
)
from plugins.user_interactions.instant_messaging.teams.utils.teams_event_data import (
    TeamsEventData,
)


@pytest.fixture
def teams_config():
    return TeamsConfig(
        PLUGIN_NAME="teams",
        TEAMS_APP_ID="app_id",
        TEAMS_APP_PASSWORD="app_password",
        ROUTE_PATH="/api/messages",
        ROUTE_METHODS=["POST"],
        TEAMS_BOT_USER_ID="bot_user_id",
        TEAMS_AUTHORIZED_CHANNELS="authorized_channel",
        TEAMS_FEEDBACK_CHANNEL="feedback_channel",
        TEAMS_FEEDBACK_BOT_USER_ID="feedback_bot_user_id",
        BEHAVIOR_PLUGIN_NAME="behavior_plugin"
    )

@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.json = AsyncMock(return_value={
        "type": "message",
        "from": {"aadObjectId": "user_id", "name": "User Name"},
        "conversation": {"id": "conversation_id", "conversationType": "personal"},
        "channelData": {"teamsChannelId": "channel_id"},
        "serviceUrl": "https://service.url",
        "id": "message_id",
        "timestamp": "2023-06-01T12:00:00Z",
        "text": "Hello, world!",
        "entities": []
    })
    request.body = AsyncMock(return_value=json.dumps(request.json.return_value).encode('utf-8'))
    request.headers = {"Authorization": "Bearer valid_token"}
    return request

@pytest.fixture
def mock_global_manager_with_teams(mock_global_manager, teams_config):
    mock_global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.INSTANT_MESSAGING = {
        "TEAMS": teams_config.dict()
    }
    return mock_global_manager

@pytest.fixture
def teams_plugin(mock_global_manager_with_teams):
    plugin = TeamsPlugin(mock_global_manager_with_teams)
    plugin.initialize()  # Ensure that initialize is called to set up adapter and credentials
    return plugin

@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.json = AsyncMock(return_value={
        "type": "message",
        "from": {"aadObjectId": "user_id"},
        "conversation": {"id": "conversation_id", "conversationType": "personal"},
        "channelData": {"teamsChannelId": "channel_id"},
        "serviceUrl": "https://service.url",
        "id": "message_id"
    })
    request.body = AsyncMock(return_value=json.dumps({
        "type": "message",
        "from": {"aadObjectId": "user_id"},
        "conversation": {"id": "conversation_id", "conversationType": "personal"},
        "channelData": {"teamsChannelId": "channel_id"},
        "serviceUrl": "https://service.url",
        "id": "message_id"
    }).encode('utf-8'))
    request.headers = {"Authorization": "Bearer valid_token"}
    return request

@pytest.mark.asyncio
async def test_initialize(teams_plugin):
    assert teams_plugin.adapter is not None
    assert teams_plugin.credentials is not None

@pytest.mark.asyncio
async def test_handle_request(teams_plugin, mock_request):
    response = await teams_plugin.handle_request(mock_request)
    assert response.status_code == 202
    response_content = json.loads(response.body)
    assert response_content["status"] == "success"
    assert response_content["message"] == "Request accepted for processing"

@pytest.mark.asyncio
async def test_process_event_data(teams_plugin, mock_request):
    event_data = await mock_request.json()
    headers = mock_request.headers
    request_json = await mock_request.json()
    with patch.object(teams_plugin, 'validate_request', return_value=AsyncMock(return_value=True)):
        await teams_plugin.process_event_data(event_data, headers, request_json)
        # Here you can add assertions based on the expected behavior of process_event_data

@pytest.mark.asyncio
async def test_validate_request(teams_plugin, mock_request):
    event_data = await mock_request.json()
    headers = mock_request.headers
    raw_body_str = await mock_request.body()

    with patch.object(teams_plugin, '_validate_auth_header', return_value=True) as mock_validate_auth_header:
        with patch.object(teams_plugin, '_authenticate_token', return_value=True) as mock_authenticate_token:
            with patch.object(teams_plugin, '_extract_user_and_channel_info', return_value=('user_id', 'channel_id', 'personal')) as mock_extract_info:
                with patch.object(teams_plugin, '_validate_user_and_channel', return_value=True) as mock_validate_user_and_channel:
                    with patch.object(teams_plugin, '_is_duplicate_request', return_value=False) as mock_is_duplicate:
                        is_valid = await teams_plugin.validate_request(event_data, headers, raw_body_str)

                        assert is_valid is True
                        mock_validate_auth_header.assert_called_once_with(headers)
                        mock_authenticate_token.assert_called_once_with(event_data, headers)
                        mock_extract_info.assert_called_once_with(event_data)
                        mock_validate_user_and_channel.assert_called_once_with('user_id', 'channel_id', 'personal')
                        mock_is_duplicate.assert_called_once_with(event_data, 'user_id', 'channel_id', 'personal')

@pytest.mark.asyncio
async def test_validate_auth_header(teams_plugin):
    valid_headers = {"Authorization": "Bearer valid_token"}
    invalid_headers = {"Authorization": "Invalid"}

    assert await teams_plugin._validate_auth_header(valid_headers) is True
    assert await teams_plugin._validate_auth_header(invalid_headers) is False

@pytest.mark.asyncio
async def test_authenticate_token(teams_plugin, mock_request):
    event_data = await mock_request.json()
    headers = mock_request.headers

    with patch('botframework.connector.auth.ChannelValidation.authenticate_channel_token_with_service_url', new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value.is_authenticated = True
        assert await teams_plugin._authenticate_token(event_data, headers) is True

        mock_auth.return_value.is_authenticated = False
        assert await teams_plugin._authenticate_token(event_data, headers) is False

def test_extract_user_and_channel_info(teams_plugin):
    event_data = {
        'from': {'aadObjectId': 'user_id'},
        'conversation': {'conversationType': 'personal'},
        'channelData': {'teamsChannelId': 'channel_id'}
    }
    user_id, channel_id, channel_type = teams_plugin._extract_user_and_channel_info(event_data)
    assert user_id == 'user_id'
    assert channel_id is None
    assert channel_type == 'personal'

    event_data['conversation']['conversationType'] = 'channel'
    user_id, channel_id, channel_type = teams_plugin._extract_user_and_channel_info(event_data)
    assert channel_id == 'channel_id'

def test_validate_user_and_channel(teams_plugin):
    teams_plugin.bot_user_id = 'bot_user_id'
    teams_plugin.teams_authorized_channels = ['authorized_channel']
    teams_plugin.teams_feedback_channel = 'feedback_channel'
    teams_plugin.teams_feedback_bot_user_id = 'feedback_bot_user_id'

    assert teams_plugin._validate_user_and_channel('user_id', 'authorized_channel', 'channel') is True
    assert teams_plugin._validate_user_and_channel('bot_user_id', 'authorized_channel', 'channel') is False
    assert teams_plugin._validate_user_and_channel('user_id', 'unauthorized_channel', 'channel') is False
    assert teams_plugin._validate_user_and_channel('user_id', 'feedback_channel', 'channel') is False
    assert teams_plugin._validate_user_and_channel('feedback_bot_user_id', 'feedback_channel', 'channel') is True
    assert teams_plugin._validate_user_and_channel('user_id', None, 'personal') is True

@pytest.mark.asyncio
async def test_is_duplicate_request(teams_plugin):
    event_data = {
        'conversation': {'id': 'conversation_id'},
        'id': 'message_id'
    }

    with patch.object(teams_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data:
        mock_read_data.return_value = None
        assert await teams_plugin._is_duplicate_request(event_data, 'user_id', 'channel_id', 'channel') is False

        mock_read_data.return_value = 'Some content'
        assert await teams_plugin._is_duplicate_request(event_data, 'user_id', 'channel_id', 'channel') is True

@pytest.mark.asyncio
async def test_send_message(teams_plugin, mock_request):
    event_data = await mock_request.json()

    # Set necessary attributes for teams_plugin
    teams_plugin.headers = mock_request.headers  # Set headers attribute
    teams_plugin.activity = Activity(
        type="message",
        service_url="https://service.url",
        conversation=ConversationAccount(id="conversation_id")  # Set conversation.id
    )

    # Mock the JWT token validation to bypass authentication
    with patch('botframework.connector.auth.JwtTokenValidation.validate_auth_header', new_callable=AsyncMock) as mock_validate_auth_header:
        mock_validate_auth_header.return_value.is_authenticated = True

        with patch('botbuilder.core.bot_framework_adapter.BotFrameworkAdapter.process_activity', new_callable=AsyncMock) as mock_process_activity:
            with patch('botbuilder.core.bot_framework_adapter.BotFrameworkAdapter.send_activities', new_callable=AsyncMock) as mock_send_activities:
                mock_send_activities.return_value = None  # Mock the response to avoid real HTTP requests
                await teams_plugin.send_message("Test message", event_data)
                mock_process_activity.assert_called_once()

@pytest.mark.asyncio
async def test_handle_request_error(teams_plugin, mock_request):
    mock_request.json.side_effect = Exception("Error parsing JSON")
    response = await teams_plugin.handle_request(mock_request)
    assert response.status_code == 500
    response_content = json.loads(response.body)
    assert response_content["status"] == "error"
    assert response_content["message"] == "Internal server error"

@pytest.mark.asyncio
async def test_process_event_data_non_message(teams_plugin, mock_request):
    event_data = await mock_request.json()
    event_data['type'] = 'non_message_type'
    headers = mock_request.headers
    request_json = event_data
    with patch.object(teams_plugin, 'validate_request', return_value=AsyncMock(return_value=True)):
        await teams_plugin.process_event_data(event_data, headers, request_json)

@pytest.mark.asyncio
async def test_validate_request_invalid_auth_header(teams_plugin, mock_request):
    event_data = await mock_request.json()
    headers = {"Authorization": "Invalid"}
    raw_body_str = await mock_request.body()
    is_valid = await teams_plugin.validate_request(event_data, headers, raw_body_str)
    assert is_valid is False

@pytest.mark.asyncio
async def test_validate_request_bot_message(teams_plugin, mock_request):
    event_data = await mock_request.json()
    event_data['from']['aadObjectId'] = teams_plugin.bot_user_id
    headers = mock_request.headers
    raw_body_str = await mock_request.body()
    is_valid = await teams_plugin.validate_request(event_data, headers, raw_body_str)
    assert is_valid is False

@pytest.mark.asyncio
async def test_request_to_notification_data(teams_plugin, mock_request):
    event_data = await mock_request.json()
    event_data['type'] = 'message'
    event_data['text'] = 'Test message'
    event_data['from'] = {'aadObjectId': 'test_user_id', 'name': 'Test User'}
    event_data['conversation'] = {'id': 'test_conversation_id'}

    with patch.object(teams_plugin, '_get_timestamp', return_value=1234567890):
        with patch.object(teams_plugin, '_create_turn_context', new_callable=AsyncMock):
            with patch.object(teams_plugin, '_extract_user_info', return_value=('test_user_id', 'Test User', 'test_channel_id')):
                with patch.object(teams_plugin, '_check_is_mention', return_value=False):
                    with patch.object(teams_plugin, '_extract_conversation_info', return_value=('conv_id', 'ts', 'thread_id', 'message')):
                        with patch.object(teams_plugin, '_process_image_attachments', new_callable=AsyncMock, return_value=[]):
                            result = await teams_plugin.request_to_notification_data(event_data)

    assert isinstance(result, TeamsEventData)
    assert result.user_id == 'test_user_id'
    assert result.text == 'Test message'
    assert result.timestamp == 'ts'
    assert result.converted_timestamp == 1234567890

@pytest.mark.asyncio
async def test_process_image_attachments(teams_plugin):
    activity = Activity(attachments=[
        Attachment(content_type="image/png", content_url="http://example.com/image.png"),
        Attachment(content_type="image/jpeg", content="data:image/jpeg;base64,base64content")
    ])

    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.content = b'image content'
        mock_get.return_value = mock_response

        with patch.object(teams_plugin, '_process_single_image_attachment', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = [
                base64.b64encode(b'image content').decode('utf-8'),
                'base64content'
            ]
            result = await teams_plugin._process_image_attachments(activity)

    assert len(result) == 2
    assert result[0] == base64.b64encode(b'image content').decode('utf-8')
    assert result[1] == 'base64content'

def test_extract_user_info(teams_plugin):
    activity = Activity(
        from_property=ChannelAccount(aad_object_id='user_id', name='User Name'),
        conversation=ConversationAccount(id='channel_id')
    )
    user_id, user_name, channel_id = teams_plugin._extract_user_info(activity)
    assert user_id == 'user_id'
    assert user_name == 'User Name'
    assert channel_id == 'channel_id'

def test_check_is_mention(teams_plugin):
    teams_plugin.bot_user_id = 'bot_id'
    activity_with_mention = Activity(
        entities=[
            Entity().deserialize({
                'type': 'mention',
                'mentioned': {'id': 'bot_id'}
            })
        ]
    )
    activity_without_mention = Activity(entities=[])

    assert teams_plugin._check_is_mention(activity_with_mention) is True
    assert teams_plugin._check_is_mention(activity_without_mention) is False

def test_extract_conversation_info(teams_plugin):
    event_data = {
        'conversation': {'id': 'conversation:id;messageid=123'},
        'id': 'message_id'
    }
    conversation_id, ts, thread_id, event_label = teams_plugin._extract_conversation_info(event_data)
    assert conversation_id == 'conversation_id;messageid=123'
    assert ts == 'message_id'
    assert thread_id == '123'
    assert event_label == 'thread_message'

    event_data['id'] = '123'
    conversation_id, ts, thread_id, event_label = teams_plugin._extract_conversation_info(event_data)
    assert event_label == 'message'

@pytest.mark.asyncio
async def test_add_reaction(teams_plugin, mock_request):
    # Créer un faux événement
    mock_event = MagicMock()

    # Configurer le plugin Teams
    teams_plugin.headers = mock_request.headers
    teams_plugin.activity = Activity(type="message")

    # Simuler l'appel à process_activity
    with patch('botbuilder.core.bot_framework_adapter.BotFrameworkAdapter.process_activity', new_callable=AsyncMock) as mock_process_activity:
        await teams_plugin.add_reaction(mock_event, "channel_id", "timestamp", "reaction_name")

        # Vérifier que process_activity a été appelé
        mock_process_activity.assert_called_once()

        # Vérifier que l'activité a été correctement configurée
        called_activity = mock_process_activity.call_args[0][0]
        assert called_activity.type == "message"
        assert called_activity.text == "special action reaction_name"

    # Vérifier que les attributs du plugin ont été correctement utilisés
    assert teams_plugin.activity.type == "message"
    assert teams_plugin.activity.text == "special action reaction_name"

@pytest.mark.asyncio
@pytest.mark.skip(reason="format_trigger_genai_message not implemented yet")
async def test_format_trigger_genai_message(teams_plugin):
    # Arrange
    message = "Test message"

    # Act
    result = await teams_plugin.format_trigger_genai_message(message)

    # Assert
    # This test will fail until the method is properly implemented
    assert result == message
    # TODO: Update this test once format_trigger_genai_message is implemented

@pytest.mark.asyncio
async def test_upload_file(teams_plugin):
    result = await teams_plugin.upload_file(None, None, None, None, None)
    assert result is None

@pytest.mark.asyncio
@pytest.mark.skip(reason="remove_reaction not implemented yet")
async def test_remove_reaction(teams_plugin):
    # Arrange
    event = None  # Mock event if needed
    channel_id = "test_channel"
    timestamp = "1234567890.123456"
    reaction_name = "test_reaction"

    # Act
    result = await teams_plugin.remove_reaction(event, channel_id, timestamp, reaction_name)

    # Assert
    # This assertion should be updated once the method is implemented
    assert result is None
    # TODO: Update this test with proper assertions once remove_reaction is implemented
