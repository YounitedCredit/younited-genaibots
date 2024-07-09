from typing import Any
from unittest.mock import MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_interactions_plugin_base import (
    GenAIInteractionsPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class MockGenAIInteractionsPlugin(GenAIInteractionsPluginBase):
    def initialize(self):
        pass

    @property
    def plugin_name(self):
        return "mock_genai_interactions_plugin"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    async def validate_request(self, event: IncomingNotificationDataBase) -> bool:
        return True

    async def handle_request(self, event: IncomingNotificationDataBase) -> Any:
        return "handle_request_result"

    async def trigger_genai(self, event: IncomingNotificationDataBase) -> Any:
        return "trigger_genai_result"

    async def handle_action(self, action_input: ActionInput, event: IncomingNotificationDataBase) -> Any:
        return "handle_action_result"

@pytest.fixture
def plugin(mock_global_manager):
    return MockGenAIInteractionsPlugin(mock_global_manager)

@pytest.fixture
def mock_event():
    return MagicMock(spec=IncomingNotificationDataBase)

@pytest.fixture
def mock_action_input():
    return MagicMock(spec=ActionInput)

@pytest.mark.asyncio
async def test_validate_request(plugin, mock_event):
    # Test validate_request method
    result = await plugin.validate_request(mock_event)
    assert result is True

@pytest.mark.asyncio
async def test_handle_request(plugin, mock_event):
    # Test handle_request method
    result = await plugin.handle_request(mock_event)
    assert result == "handle_request_result"

@pytest.mark.asyncio
async def test_trigger_genai(plugin, mock_event):
    # Test trigger_genai method
    result = await plugin.trigger_genai(mock_event)
    assert result == "trigger_genai_result"

@pytest.mark.asyncio
async def test_handle_action(plugin, mock_action_input, mock_event):
    # Test handle_action method
    result = await plugin.handle_action(mock_action_input, mock_event)
    assert result == "handle_action_result"
