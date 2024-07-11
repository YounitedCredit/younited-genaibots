from unittest.mock import MagicMock

import pytest

from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)



class DummyGenAIInteractionsTextPluginBase(GenAIInteractionsTextPluginBase):
    def __init__(self, global_manager, *args, **kwargs):
        super().__init__(global_manager, *args, **kwargs)
        self.plugin_name = self.__class__.__name__

    @property
    def plugin_name(self):
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    async def generate_completion(self, messages, event_data: IncomingNotificationDataBase):
        return "Generated completion"

    async def trigger_feedback(self, event: IncomingNotificationDataBase):
        return "Feedback triggered"

    async def handle_action(self, action_input, event):
        pass

    async def handle_request(self, event):
        pass

    async def initialize(self, *args, **kwargs):
        pass

    async def trigger_genai(self, event):
        pass

    async def validate_request(self, event):
        return True

@pytest.fixture
def mock_global_manager():
    return MagicMock(spec=GlobalManager)

@pytest.fixture
def plugin_instance(mock_global_manager):
    return DummyGenAIInteractionsTextPluginBase(global_manager=mock_global_manager)

def test_genai_cost_base_not_set(plugin_instance):
    with pytest.raises(ValueError, match="GenAI cost base is not set"):
        _ = plugin_instance.genai_cost_base

def test_genai_cost_base_setter_getter(plugin_instance):
    mock_cost_base = MagicMock(spec=GenAICostBase)
    plugin_instance.genai_cost_base = mock_cost_base
    assert plugin_instance.genai_cost_base == mock_cost_base

@pytest.mark.asyncio
async def test_generate_completion(plugin_instance):
    messages = ["message1", "message2"]
    event_data = MagicMock(spec=IncomingNotificationDataBase)
    result = await plugin_instance.generate_completion(messages, event_data)
    assert result == "Generated completion"

@pytest.mark.asyncio
async def test_trigger_feedback(plugin_instance):
    event = MagicMock(spec=IncomingNotificationDataBase)
    result = await plugin_instance.trigger_feedback(event)
    assert result == "Feedback triggered"
