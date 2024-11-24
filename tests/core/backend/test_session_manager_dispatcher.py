from unittest.mock import AsyncMock, MagicMock

import pytest

from core.backend.enriched_session import EnrichedSession
from core.backend.session_manager_dispatcher import SessionManagerDispatcher
from core.backend.session_manager_plugin_base import SessionManagerPluginBase


@pytest.fixture
def mock_global_manager():
    mock_manager = MagicMock()
    mock_manager.logger = MagicMock()
    mock_manager.bot_config = MagicMock()
    mock_manager.bot_config.SESSION_MANAGER_DEFAULT_PLUGIN_NAME = "mock_plugin"
    return mock_manager

@pytest.fixture
def mock_plugin():
    mock = MagicMock(spec=SessionManagerPluginBase)
    mock.plugin_name = "mock_plugin"
    mock.generate_session_id = MagicMock(return_value="test_session_id")
    mock.create_session = AsyncMock()
    mock.load_session = AsyncMock()
    mock.save_session = AsyncMock()
    mock.get_or_create_session = AsyncMock()
    mock.append_messages = MagicMock()
    mock.add_user_interaction_to_message = AsyncMock()
    mock.add_mind_interaction_to_message = AsyncMock()
    return mock

@pytest.fixture
def session_manager(mock_global_manager, mock_plugin):
    manager = SessionManagerDispatcher(mock_global_manager)
    manager.initialize([mock_plugin])  # Initialize with the mock plugin
    return manager

def test_generate_session_id(session_manager, mock_plugin):
    # Test
    result = session_manager.generate_session_id("channel1", "thread1")

    # Verify
    assert result == "test_session_id"
    mock_plugin.generate_session_id.assert_called_once_with("channel1", "thread1")

@pytest.mark.asyncio
async def test_create_session(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)
    mock_plugin.create_session.return_value = mock_session

    # Test
    result = await session_manager.create_session("channel1", "thread1", "start_time", True)

    # Verify
    assert result == mock_session
    mock_plugin.create_session.assert_called_once_with(
        "channel1", "thread1", "start_time", True
    )

@pytest.mark.asyncio
async def test_load_session(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)
    mock_plugin.load_session.return_value = mock_session

    # Test
    result = await session_manager.load_session("session_id")

    # Verify
    assert result == mock_session
    mock_plugin.load_session.assert_called_once_with("session_id")

@pytest.mark.asyncio
async def test_save_session(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)

    # Test
    await session_manager.save_session(mock_session)

    # Verify
    mock_plugin.save_session.assert_called_once_with(mock_session)

@pytest.mark.asyncio
async def test_get_or_create_session(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)
    mock_plugin.get_or_create_session.return_value = mock_session

    # Test
    result = await session_manager.get_or_create_session("channel1", "thread1", True)

    # Verify
    assert result == mock_session
    mock_plugin.get_or_create_session.assert_called_once_with(
        "channel1", "thread1", True
    )

def test_append_messages(session_manager, mock_plugin):
    messages = [{"message": "test1"}]
    message = {"message": "test2"}

    # Test
    session_manager.append_messages(messages, message, "session_id")

    # Verify
    mock_plugin.append_messages.assert_called_once_with(
        messages, message, "session_id"
    )

@pytest.mark.asyncio
async def test_add_user_interaction_to_message(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)
    interaction = {"type": "user_interaction"}

    # Test
    await session_manager.add_user_interaction_to_message(
        mock_session, 0, interaction
    )

    # Verify
    mock_plugin.add_user_interaction_to_message.assert_called_once_with(
        mock_session, 0, interaction
    )

@pytest.mark.asyncio
async def test_add_mind_interaction_to_message(session_manager, mock_plugin):
    mock_session = MagicMock(spec=EnrichedSession)
    interaction = {"type": "mind_interaction"}

    # Test
    await session_manager.add_mind_interaction_to_message(
        mock_session, 0, interaction
    )

    # Verify
    mock_plugin.add_mind_interaction_to_message.assert_called_once_with(
        mock_session, 0, interaction
    )

def test_get_plugin_with_non_existent_plugin(session_manager, mock_plugin):
    # Test with non-existent plugin
    result = session_manager.get_plugin("non_existent")

    # Verify it returns default plugin
    assert result == mock_plugin
    session_manager.global_manager.logger.error.assert_called_with(
        "SessionManager: Plugin 'non_existent' not found, returning default plugin"
    )

def test_get_plugin_without_name(session_manager, mock_plugin):
    # Test without specifying plugin name
    result = session_manager.get_plugin()

    # Verify it returns default plugin
    assert result == mock_plugin

def test_plugin_name_property(session_manager, mock_plugin):
    # Test getter
    result = session_manager.plugin_name
    assert result == "mock_plugin"

    # Test setter
    session_manager.plugin_name = "new_name"
    assert mock_plugin.plugin_name == "new_name"

def test_plugins_property(session_manager, mock_plugin):
    # Test getter
    assert session_manager.plugins == [mock_plugin]

    # Test setter
    new_mock_plugin = MagicMock(spec=SessionManagerPluginBase)
    session_manager.plugins = [new_mock_plugin]
    assert session_manager.plugins == [new_mock_plugin]
