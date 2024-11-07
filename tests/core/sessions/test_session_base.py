import json
from datetime import datetime
from unittest.mock import patch

from core.backend.session_manager_plugin_base import SessionBase


def test_session_base_initialization():
    """
    Test the initialization of the SessionBase class.
    """
    session = SessionBase(session_id="test_session")

    assert session.session_id == "test_session"
    assert isinstance(session.start_time, str)
    # Validate that the start_time is a proper ISO formatted datetime string
    assert datetime.fromisoformat(session.start_time)  # Should not raise an error
    assert session.end_time is None
    assert session.events == []

def test_session_base_add_event():
    """
    Test that events are added correctly to the session.
    """
    session = SessionBase(session_id="test_session")
    event_data = {"key": "value"}

    # Mock datetime to control the event's timestamp
    with patch("core.sessions.session_base.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 10, 1, 10, 30)
        session.add_event("test_event", event_data)

    assert len(session.events) == 1
    event = session.events[0]
    assert event["type"] == "test_event"
    assert event["data"] == event_data
    assert event["timestamp"] == mock_datetime.now.return_value.isoformat()

def test_session_base_end_session():
    """
    Test that the session's end time is set correctly when ending the session.
    """
    session = SessionBase(session_id="test_session")

    # Mock datetime to control the end time
    with patch("core.sessions.session_base.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 10, 1, 10, 30)
        session.end_session()

    assert session.end_time == mock_datetime.now.return_value.isoformat()

def test_session_base_end_session_with_custom_time():
    """
    Test that a custom end time can be provided when ending the session.
    """
    session = SessionBase(session_id="test_session")
    custom_end_time = "2024-10-01T10:45:00"

    session.end_session(end_time=custom_end_time)

    assert session.end_time == custom_end_time

def test_session_base_to_dict():
    """
    Test that the session is correctly converted to a dictionary.
    """
    session = SessionBase(session_id="test_session")
    session.add_event("test_event", {"key": "value"})
    session.end_session(end_time="2024-10-01T10:45:00")

    session_dict = session.to_dict()

    expected_dict = {
        "session_id": "test_session",
        "start_time": session.start_time,
        "end_time": "2024-10-01T10:45:00",
        "events": [{
            "type": "test_event",
            "data": {"key": "value"},
            "timestamp": session.events[0]["timestamp"]
        }]
    }

    assert session_dict == expected_dict

def test_session_base_to_json():
    """
    Test that the session is correctly converted to a JSON string.
    """
    session = SessionBase(session_id="test_session")
    session.add_event("test_event", {"key": "value"})
    session.end_session(end_time="2024-10-01T10:45:00")

    session_json = session.to_json()

    expected_json = json.dumps({
        "session_id": "test_session",
        "start_time": session.start_time,
        "end_time": "2024-10-01T10:45:00",
        "events": [{
            "type": "test_event",
            "data": {"key": "value"},
            "timestamp": session.events[0]["timestamp"]
        }]
    }, indent=2)

    assert session_json == expected_json
