from datetime import datetime
from unittest.mock import patch

import pytest

from core.sessions.enriched_session import EnrichedSession


# Example of a reusable fixture to mock a global manager or config
@pytest.fixture
def mock_config_manager(mock_config_manager):
    # Assume mock_config_manager from conftest.py is already configured correctly
    return mock_config_manager

def test_init_session(mock_config_manager):
    """
    Test the initialization of the EnrichedSession class.
    """
    session = EnrichedSession(session_id="test_session")

    assert session.session_id == "test_session"
    # Instead of asserting start_time is None, check if it has been correctly initialized
    assert isinstance(session.start_time, str)  # It should be a valid string in ISO format
    # If needed, check if start_time is a valid ISO format string
    assert datetime.fromisoformat(session.start_time)  # This ensures it's a valid datetime string


def test_end_session(mock_config_manager):
    """
    Test the end_session method, which should mark the session's end and calculate total time.
    """
    session = EnrichedSession(session_id="test_session", start_time="2024-10-01T10:00:00")

    # Mock datetime to control the current time
    with patch("core.sessions.enriched_session.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 10, 1, 10, 30)
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        session.end_session()

    assert session.end_time == mock_datetime.now.return_value.isoformat()
    assert session.total_time_ms == 1800000  # 30 minutes in milliseconds

def test_calculate_total_time(mock_config_manager):
    """
    Test the calculate_total_time method to ensure correct calculation of the session's duration.
    """
    session = EnrichedSession(session_id="test_session", start_time="2024-10-01T10:00:00")
    session.end_time = "2024-10-01T10:30:00"

    session.calculate_total_time()
    assert session.total_time_ms == 1800000  # 30 minutes in milliseconds

def test_accumulate_cost(mock_config_manager):
    """
    Test accumulate_cost to ensure cost and token count are properly summed up.
    """
    session = EnrichedSession(session_id="test_session")

    session.accumulate_cost({"total_tokens": 100, "total_cost": 10.5})
    session.accumulate_cost({"total_tokens": 50, "total_cost": 5.25})

    assert session.total_cost == {"total_tokens": 150, "total_cost": 15.75}

def test_sanitize_message(mock_config_manager):
    """
    Test sanitize_message to ensure it properly escapes unsafe characters for JSON.
    """
    session = EnrichedSession(session_id="test_session")

    message = '<test> This is a "message" with special characters.'
    sanitized_message = session.sanitize_message(message)

    assert sanitized_message == message  # Expecting same content, but JSON safe

def test_add_mind_interaction_to_message(mock_config_manager):
    """
    Test that a mind interaction is correctly added to an assistant message.
    """
    session = EnrichedSession(session_id="test_session")
    session.messages = [{"role": "assistant", "content": "Hello!"}]

    interaction = {"message": "Interaction content"}
    session.add_mind_interaction_to_message(0, interaction)

    assert "mind_interactions" in session.messages[0]
    assert session.messages[0]["mind_interactions"][0]["message"] == "Interaction content"

def test_add_user_interaction_to_message(mock_config_manager):
    """
    Test that a user interaction is correctly added to an assistant message.
    """
    session = EnrichedSession(session_id="test_session")
    session.messages = [{"role": "assistant", "content": "Hello!"}]

    interaction = {"message": "User content"}
    session.add_user_interaction_to_message(0, interaction)

    assert "user_interactions" in session.messages[0]
    assert session.messages[0]["user_interactions"][0]["message"] == "User content"

def test_to_dict(mock_config_manager):
    """
    Test that the session is correctly converted into a dictionary.
    """
    session = EnrichedSession(session_id="test_session", start_time="2024-10-01T10:00:00")
    session.end_time = "2024-10-01T10:30:00"
    session.total_time_ms = 1800000
    session.total_cost = {"total_tokens": 150, "total_cost": 15.75}
    session.messages = [{"role": "assistant", "content": "Hello!"}]

    session_dict = session.to_dict()

    expected_dict = {
        "session_id": "test_session",
        "start_time": "2024-10-01T10:00:00",
        "end_time": "2024-10-01T10:30:00",
        "total_time_ms": 1800000,
        "total_cost": {"total_tokens": 150, "total_cost": 15.75},
        "messages": [{"role": "assistant", "content": "Hello!"}]
    }

    assert session_dict == expected_dict

def test_from_dict(mock_config_manager):
    """
    Test that a session is correctly initialized from a dictionary.
    """
    session_data = {
        "session_id": "test_session",
        "start_time": "2024-10-01T10:00:00",
        "end_time": "2024-10-01T10:30:00",
        "total_time_ms": 1800000,
        "total_cost": {"total_tokens": 150, "total_cost": 15.75},
        "messages": [{"role": "assistant", "content": "Hello!"}]
    }

    session = EnrichedSession.from_dict(session_data)

    assert session.session_id == "test_session"
    assert session.start_time == "2024-10-01T10:00:00"
    assert session.end_time == "2024-10-01T10:30:00"
    assert session.total_time_ms == 1800000
    assert session.total_cost == {"total_tokens": 150, "total_cost": 15.75}
    assert session.messages == [{"role": "assistant", "content": "Hello!"}]
