import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.sessions.enriched_session import EnrichedSession
from core.sessions.session_base import SessionBase
from core.sessions.session_manager import SessionManager


@pytest.fixture
def mock_global_manager():
    """
    Fixture to create a mock GlobalManager with a mock logger and backend dispatcher.
    """
    global_manager = MagicMock()
    global_manager.logger = MagicMock()
    global_manager.backend_internal_data_processing_dispatcher = MagicMock()
    return global_manager

@pytest.fixture
def session_manager(mock_global_manager):
    """
    Fixture to create the SessionManager instance with a mocked GlobalManager.
    """
    manager = SessionManager(mock_global_manager)
    manager.initialize()  # Ensure that the backend dispatcher is initialized
    return manager

@pytest.mark.asyncio
async def test_initialize(session_manager, mock_global_manager):
    """
    Test the initialize method of SessionManager to ensure it sets up the backend dispatcher.
    """
    session_manager.initialize()

    assert session_manager.backend_dispatcher == mock_global_manager.backend_internal_data_processing_dispatcher

def test_generate_session_id(session_manager):
    """
    Test session ID generation.
    """
    session_id = session_manager.generate_session_id("channel_123", "thread_456")
    assert session_id == "channel_123_thread_456.json"

@pytest.mark.asyncio
async def test_create_session(session_manager):
    """
    Test session creation for both EnrichedSession and SessionBase.
    """
    # Test creating a regular session
    session = await session_manager.create_session("channel_123", "thread_456")
    assert isinstance(session, SessionBase)
    assert session.session_id == "channel_123_thread_456.json"

    # Test creating an enriched session
    enriched_session = await session_manager.create_session("channel_123", "thread_456", enriched=True)
    assert isinstance(enriched_session, EnrichedSession)
    assert enriched_session.session_id == "channel_123_thread_456.json"

@pytest.mark.asyncio
async def test_load_session(session_manager, mock_global_manager):
    """
    Test loading a session from the backend dispatcher.
    """
    session_data = {
        "session_id": "channel_123_thread_456.json",
        "start_time": "2024-10-01T10:00:00",
        "end_time": "2024-10-01T10:30:00",
        "total_time_ms": 1800000,
        "total_cost": {"total_tokens": 150, "total_cost": 15.75},
        "messages": []
    }
    session_json = json.dumps(session_data)

    # Mock the backend dispatcher to return a session
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=session_json)

    session = await session_manager.load_session("channel_123_thread_456.json")

    assert isinstance(session, EnrichedSession)
    assert session.session_id == "channel_123_thread_456.json"
    assert session.start_time == "2024-10-01T10:00:00"
    assert session.end_time == "2024-10-01T10:30:00"

@pytest.mark.asyncio
async def test_load_session_not_found(session_manager, mock_global_manager):
    """
    Test loading a session that doesn't exist.
    """
    # Mock the backend dispatcher to return None (session not found)
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)

    session = await session_manager.load_session("non_existent_session.json")
    assert session is None

@pytest.mark.asyncio
async def test_save_session(session_manager, mock_global_manager):
    """
    Test saving a session by serializing it to JSON and storing it via the backend dispatcher.
    """
    session = EnrichedSession(session_id="channel_123_thread_456.json", start_time="2024-10-01T10:00:00")

    # Mock the backend dispatcher save method
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    await session_manager.save_session(session)

    # Check if the backend's write method was called with the correct session JSON
    session_json = json.dumps(session.to_dict(), default=str)
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        mock_global_manager.backend_internal_data_processing_dispatcher.sessions, session.session_id, session_json
    )

@pytest.mark.asyncio
async def test_add_user_interaction_to_message(session_manager, mock_global_manager):
    """
    Test adding a user interaction to a session's message.
    """
    session = EnrichedSession(session_id="channel_123_thread_456.json")
    session.messages = [{"role": "assistant", "content": "Hello!"}]

    interaction = {"message": "User content"}

    # Mock the save session method to avoid real backend calls
    session_manager.save_session = AsyncMock()

    await session_manager.add_user_interaction_to_message(session, 0, interaction)

    assert "user_interactions" in session.messages[0]
    assert session.messages[0]["user_interactions"][0]["message"] == "User content"
    session_manager.save_session.assert_called_once_with(session)

@pytest.mark.asyncio
async def test_get_or_create_session_new(session_manager, mock_global_manager):
    """
    Test creating a new session when no existing session is found.
    """
    # Mock backend to return no existing session
    session_manager.load_session = AsyncMock(return_value=None)

    # Patch datetime.now() to control the start_time value
    with patch("core.sessions.session_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 10, 3, 15, 58, 21, 689422)
        start_time = mock_datetime.now.return_value.isoformat()

        # Mock create_session to return an EnrichedSession
        session_manager.create_session = AsyncMock(return_value=EnrichedSession("channel_123_thread_456.json"))

        # Call the method to test
        session = await session_manager.get_or_create_session("channel_123", "thread_456")

        # Check if the session is of the correct type and has the correct session_id
        assert isinstance(session, EnrichedSession)
        assert session.session_id == "channel_123_thread_456.json"

        # Ensure create_session was called with the correct arguments, including the start_time
        session_manager.create_session.assert_called_once_with("channel_123", "thread_456", start_time, False)
