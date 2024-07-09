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
