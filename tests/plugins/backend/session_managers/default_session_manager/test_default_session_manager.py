import json
from unittest.mock import AsyncMock

import pytest

from core.backend.enriched_session import EnrichedSession
from plugins.backend.session_managers.default_session_manager.default_session_manager import (
    DefaultSessionManagerPlugin,
)


@pytest.fixture
def session_manager(mock_global_manager):
    plugin = DefaultSessionManagerPlugin(mock_global_manager)
    plugin.backend_dispatcher = AsyncMock()
    plugin.backend_dispatcher.sessions = "sessions"
    mock_global_manager.bot_config.BOT_UNIQUE_ID = "test_bot"
    plugin.initialize()
    return plugin

@pytest.mark.asyncio
async def test_get_or_create_session_new(session_manager):
    session_manager.backend_dispatcher.read_data_content.return_value = None
    session = await session_manager.get_or_create_session("channel1", "thread1", True)
    assert session.session_id == "test_bot_channel1_thread1.json"
    assert isinstance(session, EnrichedSession)

@pytest.mark.asyncio
async def test_get_or_create_session_existing(session_manager):
    existing_session = EnrichedSession("test_bot_channel1_thread1.json")
    session_manager.sessions = {"test_bot_channel1_thread1.json": existing_session}
    session = await session_manager.get_or_create_session("channel1", "thread1")
    assert session is existing_session

@pytest.mark.asyncio
async def test_save_session(session_manager):
    session = EnrichedSession("test_session")
    await session_manager.save_session(session)
    session_manager.backend_dispatcher.write_data_content.assert_called_once()

@pytest.mark.asyncio
async def test_add_user_interaction(session_manager):
    session = EnrichedSession("test_session")
    session.messages = [{"role": "assistant", "content": "test"}]
    interaction = {"type": "reaction", "value": "👍", "message": "test reaction"}

    await session_manager.add_user_interaction_to_message(session, 0, interaction)
    assert "user_interactions" in session.messages[0]
    assert session.messages[0]["user_interactions"][0] == interaction

@pytest.mark.asyncio
async def test_add_user_interaction_non_assistant(session_manager):
    session = EnrichedSession("test_session")
    session.messages = [{"role": "user", "content": "test"}]
    interaction = {"type": "reaction", "value": "👍", "message": "test"}

    await session_manager.add_user_interaction_to_message(session, 0, interaction)
    assert "user_interactions" not in session.messages[0]

@pytest.mark.asyncio
async def test_add_mind_interaction(session_manager):
    session = EnrichedSession("test_session")
    session.messages = [{"role": "assistant", "content": "test"}]
    interaction = {"message": "thinking...", "timestamp": "2024-01-01"}

    await session_manager.add_mind_interaction_to_message(session, 0, interaction)
    assert session.messages[0]["mind_interactions"] == [interaction]

def test_generate_session_id(session_manager):
    session_id = session_manager.generate_session_id("channel1", "thread1")
    assert session_id == "test_bot_channel1_thread1.json"

def test_sanitize_message(session_manager):
    message = 'Test "message" with special chars: \n\t'
    sanitized = session_manager.sanitize_message(message)
    assert isinstance(sanitized, str)
    assert json.loads(json.dumps(sanitized)) == sanitized
