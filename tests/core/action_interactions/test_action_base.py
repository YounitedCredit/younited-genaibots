# tests/core/action_interactions/test_action_base.py

from unittest.mock import MagicMock

import pytest

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


# Création d'une classe concrète pour les tests
class ConcreteAction(ActionBase):
    def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        return "Executed"

@pytest.fixture
def global_manager():
    from core.global_manager import GlobalManager
    return MagicMock(spec=GlobalManager)

@pytest.fixture
def action_input():
    return MagicMock(spec=ActionInput)

@pytest.fixture
def incoming_event():
    return MagicMock(spec=IncomingNotificationDataBase)

@pytest.fixture
def concrete_action(global_manager):
    return ConcreteAction(global_manager)

def test_concrete_action_initialization(concrete_action):
    assert concrete_action is not None
    assert isinstance(concrete_action.global_manager, MagicMock)

def test_concrete_action_execute(concrete_action, action_input, incoming_event):
    result = concrete_action.execute(action_input, incoming_event)
    assert result == "Executed"
