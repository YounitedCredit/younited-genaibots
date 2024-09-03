from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.user_interactions.custom_api.generic_rest.generic_rest import (
    GenericRestPlugin,
    RestConfig,
)

from core.user_interactions.outgoing_notification_data_base import (
    OutgoingNotificationDataBase,
)

class RestConfig(BaseModel):
    PLUGIN_NAME: str
    ROUTE_PATH: str
    ROUTE_METHODS: List[str]
    BEHAVIOR_PLUGIN_NAME: str
    MESSAGE_URL: str
    REACTION_URL: str

@pytest.fixture
def rest_config_data():
    return {
        "PLUGIN_NAME": "generic_rest",
        "ROUTE_PATH": "/webhook",
        "ROUTE_METHODS": ["POST"],
        "BEHAVIOR_PLUGIN_NAME": "behavior_plugin",
        "MESSAGE_URL": "http://example.com/message",
        "REACTION_URL": "http://example.com/reaction"
    }

@pytest.fixture
def generic_rest_plugin(mock_global_manager, rest_config_data):
    mock_global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.CUSTOM_API = {
        "GENERIC_REST": rest_config_data
    }
    # Créez un mock pour asyncio.get_event_loop()
    mock_loop = AsyncMock()
    mock_loop.create_task = MagicMock()
    
    # Remplacez asyncio.get_event_loop() par notre mock
    with patch('asyncio.get_event_loop', return_value=mock_loop):
        plugin = GenericRestPlugin(mock_global_manager)
        yield plugin

@pytest.mark.asyncio
async def test_handle_request(generic_rest_plugin):
    # Test case 1: Valid request
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=b'{"user_id": "123", "channel_id": "456"}')
    request.headers = {}
    request.url.path = "/webhook"

    response = await generic_rest_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 202
    assert response.body == b"Request accepted for processing"

    # Test case 2: Invalid JSON
    request.body = AsyncMock(return_value=b'{"invalid": "json"')
    response = await generic_rest_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 400
    assert response.body == b"Invalid JSON"

    # Test case 3: General exception
    request.body = AsyncMock(side_effect=Exception("Test exception"))
    response = await generic_rest_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 500
    assert response.body == b"Internal server error"

    # Verify that create_task was called
    assert generic_rest_plugin.global_manager.loop.create_task.called

@pytest.mark.asyncio
async def test_validate_request(generic_rest_plugin):
    event_data = {
        "user_id": "123",
        "channel_id": "456",
        "event_type": "test_event",
        "data": {"key": "value"}
    }
    headers = {}
    raw_body_str = '{"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}'

    # Mock IncomingNotificationDataBase.from_dict to match the event_data structure
    IncomingNotificationDataBase.from_dict = MagicMock(return_value=MagicMock())

    is_valid = await generic_rest_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is True

    # Test with missing keys in event_data
    event_data_missing_keys = {
        "user_id": "123"
    }
    raw_body_str_missing_keys = '{"user_id": "123"}'
    is_valid = await generic_rest_plugin.validate_request(event_data_missing_keys, headers, raw_body_str_missing_keys)
    
    assert is_valid is False

    # Test with invalid JSON
    raw_body_str_invalid_json = '{"user_id": "123", "channel_id": 456"'
    is_valid = await generic_rest_plugin.validate_request(event_data, headers, raw_body_str_invalid_json)
    
    assert is_valid is False

@pytest.mark.asyncio
async def test_process_event_data(generic_rest_plugin):
    event_data = {
        "user_id": "123",
        "channel_id": "456",
        "event_type": "test_event",
        "data": {"key": "value"}
    }
    headers = {}
    raw_body_str = '{"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}'

    # Mock the behavior dispatcher
    generic_rest_plugin.global_manager.user_interactions_behavior_dispatcher.process_interaction = AsyncMock()

    await generic_rest_plugin.process_event_data(event_data, headers, raw_body_str)

    # Add assertions to verify expected behavior
    assert generic_rest_plugin.global_manager.user_interactions_behavior_dispatcher.process_interaction.called

    # Test with invalid request data
    with patch.object(generic_rest_plugin, 'validate_request', return_value=False):
        await generic_rest_plugin.process_event_data(event_data, headers, raw_body_str)
        assert not generic_rest_plugin.global_manager.user_interactions_behavior_dispatcher.process_interaction.called

@pytest.mark.asyncio
async def test_send_message(generic_rest_plugin):
    message = "Hello, world!"
    event = MagicMock()
    message_type = MessageType.TEXT

    # Mock the post_notification method
    generic_rest_plugin.post_notification = AsyncMock()

    await generic_rest_plugin.send_message(message, event, message_type)

    # Add assertions to verify the notification was sent
    assert generic_rest_plugin.post_notification.called

    # Test with an exception during post_notification
    generic_rest_plugin.post_notification.side_effect = Exception("Failed to send message")
    with pytest.raises(Exception):
        await generic_rest_plugin.send_message(message, event, message_type)

@pytest.mark.asyncio
async def test_add_reaction(generic_rest_plugin):
    event = MagicMock()
    channel_id = "123"
    timestamp = "1234567890"
    reaction_name = "like"

    # Mock the post_notification method
    generic_rest_plugin.post_notification = AsyncMock()

    await generic_rest_plugin.add_reaction(event, channel_id, timestamp, reaction_name)

    # Add assertions to verify the reaction notification was sent
    assert generic_rest_plugin.post_notification.called

    # Test with an exception during post_notification
    generic_rest_plugin.post_notification.side_effect = Exception("Failed to add reaction")
    with pytest.raises(Exception):
        await generic_rest_plugin.add_reaction(event, channel_id, timestamp, reaction_name)

@pytest.mark.asyncio
async def test_remove_reaction(generic_rest_plugin):
    event = MagicMock()
    channel_id = "123"
    timestamp = "1234567890"
    reaction_name = "like"

    # Mock the post_notification method
    generic_rest_plugin.post_notification = AsyncMock()

    await generic_rest_plugin.remove_reaction(event, channel_id, timestamp, reaction_name)

    # Add assertions to verify the reaction removal notification was sent
    assert generic_rest_plugin.post_notification.called

    # Test with an exception during post_notification
    generic_rest_plugin.post_notification.side_effect = Exception("Failed to remove reaction")
    with pytest.raises(Exception):
        await generic_rest_plugin.remove_reaction(event, channel_id, timestamp, reaction_name)

@pytest.mark.asyncio
async def test_request_to_notification_data(generic_rest_plugin):
    event_data = {
        "user_id": "123",
        "channel_id": "456",
        "event_type": "test_event",
        "data": {"key": "value"}
    }

    notification_data = await generic_rest_plugin.request_to_notification_data(event_data)

    assert isinstance(notification_data, IncomingNotificationDataBase)
    assert notification_data.user_id == "123"
    assert notification_data.channel_id == "456"

@pytest.mark.asyncio
async def test_post_notification(generic_rest_plugin):
    notification = MagicMock(spec=OutgoingNotificationDataBase)
    url = "http://example.com/post_notification"

    # Mock the aiohttp.ClientSession and response
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        await generic_rest_plugin.post_notification(notification, url)

        mock_post.assert_called_once()

        # Test case when the response is not successful
        mock_response.status = 500
        with pytest.raises(Exception):
            await generic_rest_plugin.post_notification(notification, url)

@pytest.mark.asyncio
async def test_initialize(generic_rest_plugin):
    # Test if the initialize method sets up the correct attributes
    generic_rest_plugin.initialize()

    assert generic_rest_plugin.route_path == "/webhook"
    assert generic_rest_plugin.route_methods == ["POST"]
    assert generic_rest_plugin.plugin_name == "generic_rest"
    assert generic_rest_plugin.reactions is not None

def test_route_path(generic_rest_plugin):
    # Ensure the plugin is initialized first
    generic_rest_plugin.initialize()
    assert generic_rest_plugin.route_path == "/webhook"

def test_route_methods(generic_rest_plugin):
    # Ensure the plugin is initialized first
    generic_rest_plugin.initialize()
    assert generic_rest_plugin.route_methods == ["POST"]

def test_plugin_name_getter(generic_rest_plugin):
    # Ensure the plugin is initialized first
    generic_rest_plugin.initialize()
    assert generic_rest_plugin.plugin_name == "generic_rest"

@pytest.mark.asyncio
async def test_handle_request_valid_request(generic_rest_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=b'{"user_id": "123", "channel_id": "456"}')
    request.headers = {}
    request.url.path = "/webhook"

    with patch.object(generic_rest_plugin, 'process_event_data', return_value=AsyncMock()) as mock_process_event:
        response = await generic_rest_plugin.handle_request(request)
        mock_process_event.assert_called_once()
        assert isinstance(response, Response)
        assert response.status_code == 202
        assert response.body == b"Request accepted for processing"

@pytest.mark.asyncio
async def test_handle_request_invalid_json(generic_rest_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=b'{"invalid_json"}')
    request.headers = {}
    request.url.path = "/webhook"

    response = await generic_rest_plugin.handle_request(request)
    assert isinstance(response, Response)
    assert response.status_code == 400
    assert response.body == b"Invalid JSON"

@pytest.mark.asyncio
async def test_handle_request_general_exception(generic_rest_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(side_effect=Exception("Test exception"))
    request.headers = {}
    request.url.path = "/webhook"

    response = await generic_rest_plugin.handle_request(request)
    assert isinstance(response, Response)
    assert response.status_code == 500
    assert response.body == b"Internal server error"

    # Test case for Exception with missing Referer header
    request.headers.get.return_value = None
    response = await generic_rest_plugin.handle_request(request)
    assert isinstance(response, Response)
    assert response.status_code == 500
    assert response.body == b"Internal server error"

@pytest.mark.asyncio
async def test_validate_request_missing_keys(generic_rest_plugin):
    event_data = {"user_id": "123"}
    headers = {}
    raw_body_str = '{"user_id": "123"}'

    is_valid = await generic_rest_plugin.validate_request(event_data, headers, raw_body_str)
    assert not is_valid

@pytest.mark.asyncio
async def test_process_event_data_with_invalid_request(generic_rest_plugin):
    event_data = {"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}
    headers = {}
    raw_body_str = '{"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}'

    with patch.object(generic_rest_plugin, 'validate_request', return_value=False):
        await generic_rest_plugin.process_event_data(event_data, headers, raw_body_str)
        generic_rest_plugin.global_manager.user_interactions_behavior_dispatcher.process_interaction.assert_not_called()

@pytest.mark.asyncio
async def test_process_event_data_exception_handling(generic_rest_plugin):
    event_data = {"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}
    headers = {}
    raw_body_str = '{"user_id": "123", "channel_id": "456", "event_type": "test_event", "data": {"key": "value"}}'

    with patch.object(generic_rest_plugin, 'validate_request', return_value=True):
        with patch.object(generic_rest_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_interaction', side_effect=Exception("Test exception")):
            with pytest.raises(Exception):
                await generic_rest_plugin.process_event_data(event_data, headers, raw_body_str)

@pytest.mark.asyncio
async def test_post_notification_success(generic_rest_plugin):
    notification = MagicMock(spec=OutgoingNotificationDataBase)
    url = "http://example.com/post_notification"

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        await generic_rest_plugin.post_notification(notification, url)
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_post_notification_failure(generic_rest_plugin):
    notification = MagicMock(spec=OutgoingNotificationDataBase)
    url = "http://example.com/post_notification"

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status = 500
        mock_post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(Exception):
            await generic_rest_plugin.post_notification(notification, url)
