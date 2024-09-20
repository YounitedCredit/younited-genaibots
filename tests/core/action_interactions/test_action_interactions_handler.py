# tests/core/action_interactions/test_action_interactions_handler.py

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_interactions_handler import (
    ActionInteractionsHandler,
)
from core.genai_interactions.genai_response import GenAIResponse
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions_behaviors.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)


@pytest.fixture
def global_manager():
    from core.global_manager import GlobalManager
    global_manager = MagicMock(spec=GlobalManager)
    global_manager.plugin_manager = MagicMock()
    global_manager.logger = MagicMock()
    global_manager.user_interactions_dispatcher = MagicMock(spec=UserInteractionsDispatcher)
    return global_manager

@pytest.fixture
def action_interactions_handler(global_manager):
    return ActionInteractionsHandler(global_manager)

@pytest.fixture
def genai_response():
    response = MagicMock(spec=GenAIResponse)
    response.response = []
    return response

@pytest.fixture
def event():
    return MagicMock(spec=IncomingNotificationDataBase)

@pytest.fixture
def action():
    action = MagicMock()
    action.ActionName = 'test_action'
    action.Parameters = {'param1': 'value1'}
    return action

@pytest.fixture
def action_plugin():
    plugin = AsyncMock(spec=ActionBase)
    plugin.execute = AsyncMock(return_value='executed')
    return plugin

def test_action_interactions_handler_initialization(action_interactions_handler, global_manager):
    assert action_interactions_handler.global_manager == global_manager
    assert action_interactions_handler.plugin_manager == global_manager.plugin_manager
    assert action_interactions_handler.logger == global_manager.logger
    assert action_interactions_handler.im_dispatcher == global_manager.user_interactions_dispatcher

@pytest.mark.asyncio
async def test_handle_action_success(action_interactions_handler, global_manager, action, event, action_plugin):
    global_manager.get_action.return_value = action_plugin
    result = await action_interactions_handler.handle_action(action, event)
    assert result == 'executed'
    action_plugin.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_action_failure(action_interactions_handler, global_manager, action, event, action_plugin):
    global_manager.get_action.return_value = action_plugin
    action_plugin.execute.side_effect = Exception("test error")
    result = await action_interactions_handler.handle_action(action, event)
    assert result is None
    action_plugin.execute.assert_awaited_once()
    action_interactions_handler.logger.error.assert_called_once()
    action_interactions_handler.im_dispatcher.send_message.assert_any_await(event, "An error occurred while executing the action test_action: test error", is_internal=True)
    action_interactions_handler.im_dispatcher.send_message.assert_any_await(event, "There was a technical issue while processing your query, try again or ask for help to the bot admin !", is_internal=False)

@pytest.mark.asyncio
async def test_handle_request(action_interactions_handler, genai_response, event):
    action1 = MagicMock()
    action1.ActionName = 'ObservationThought'
    action1.Parameters = {'param1': 'value1'}
    action2 = MagicMock()
    action2.ActionName = 'UserInteraction'
    action2.Parameters = {'param2': 'value2'}
    genai_response.response = [action1, action2]

    action_interactions_handler.handle_action = AsyncMock()
    await action_interactions_handler.handle_request(genai_response, event)
    action_interactions_handler.handle_action.assert_any_await(action1, event)
    action_interactions_handler.handle_action.assert_any_await(action2, event)
