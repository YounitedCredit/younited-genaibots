from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.reaction_base import ReactionBase
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)


class TestUserInteractionsPlugin(UserInteractionsPluginBase):
    """
    A concrete implementation of UserInteractionsPluginBase for testing purposes.
    """

    def __init__(self, global_manager):
        self.global_manager = global_manager
        self._reactions = None
        self._plugin_name = "test_plugin"

    @property
    def route_path(self):
        return "/test_route"

    @property
    def route_methods(self):
        return ["GET", "POST"]

    @property
    def reactions(self) -> ReactionBase:
        return self._reactions

    @reactions.setter
    def reactions(self, value: ReactionBase):
        self._reactions = value

    def validate_request(self, request):
        return True

    def handle_request(self, request):
        return "handled"

    async def send_message(self, message, event: IncomingNotificationDataBase, message_type=MessageType.TEXT, title=None, is_internal=False, show_ref=False):
        return "message sent"

    async def upload_file(self, event: IncomingNotificationDataBase, file_content, filename, title, is_internal=False):
        return "file uploaded"

    async def add_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        return "reaction added"

    async def remove_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name):
        return "reaction removed"

    def request_to_notification_data(self, event_data):
        return "notification data"

    def format_trigger_genai_message(self, message):
        return "formatted message"

    async def process_event_data(self, event_data, headers, request_json):
        return "processed event data"

    def initialize(self, plugins):
        pass  # Implementation of initialize method

    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        # Returning a mocked conversation history for testing purposes
        return [event]  # Mocked list with the event as the conversation history.

    @property
    def plugin_name(self):
        return self._plugin_name

@pytest.fixture
def test_plugin(mock_global_manager):
    return TestUserInteractionsPlugin(mock_global_manager)

def test_route_path(test_plugin):
    assert test_plugin.route_path == "/test_route"

def test_route_methods(test_plugin):
    assert test_plugin.route_methods == ["GET", "POST"]

def test_reactions(test_plugin, mock_reaction_base):
    test_plugin.reactions = mock_reaction_base
    assert test_plugin.reactions == mock_reaction_base

def test_validate_request(test_plugin):
    request = MagicMock()
    assert test_plugin.validate_request(request)

def test_handle_request(test_plugin):
    request = MagicMock()
    assert test_plugin.handle_request(request) == "handled"

@pytest.mark.asyncio
async def test_send_message(test_plugin, mock_incoming_notification_data_base):
    result = await test_plugin.send_message("test_message", mock_incoming_notification_data_base)
    assert result == "message sent"

@pytest.mark.asyncio
async def test_upload_file(test_plugin, mock_incoming_notification_data_base):
    result = await test_plugin.upload_file(mock_incoming_notification_data_base, "file_content", "filename", "title")
    assert result == "file uploaded"

@pytest.mark.asyncio
async def test_add_reaction(test_plugin, mock_incoming_notification_data_base):
    result = await test_plugin.add_reaction(mock_incoming_notification_data_base, "channel_id", "timestamp", "reaction_name")
    assert result == "reaction added"

@pytest.mark.asyncio
async def test_remove_reaction(test_plugin, mock_incoming_notification_data_base):
    result = await test_plugin.remove_reaction(mock_incoming_notification_data_base, "channel_id", "timestamp", "reaction_name")
    assert result == "reaction removed"

def test_request_to_notification_data(test_plugin):
    event_data = MagicMock()
    result = test_plugin.request_to_notification_data(event_data)
    assert result == "notification data"

def test_format_trigger_genai_message(test_plugin):
    message = "test message"
    result = test_plugin.format_trigger_genai_message(message)
    assert result == "formatted message"

@pytest.mark.asyncio
async def test_process_event_data(test_plugin):
    event_data = MagicMock()
    headers = {"header": "value"}
    request_json = "request json"
    result = await test_plugin.process_event_data(event_data, headers, request_json)
    assert result == "processed event data"
