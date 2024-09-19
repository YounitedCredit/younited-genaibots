from plugins.user_interactions.instant_messaging.teams.utils.teams_event_data import (
    TeamsEventData,
)


def test_teams_event_data_instantiation():
    # Example data for IncomingNotificationDataBase attributes
    event_data = {
        "timestamp": "2023-01-01T00:00:00.000Z",
        "event_label": "message",
        "channel_id": "channel_id",
        "thread_id": "thread_id",
        "response_id": "response_id",
        "user_name": "user_name",
        "user_email": "user_email",
        "user_id": "user_id",
        "is_mention": False,
        "text": "text",
        "images": [],
        "files_content": [],
        "origin": "origin",
        "raw_data": {},
        "origin_plugin_name": "origin_plugin_name"
    }

    # Create an instance of TeamsEventData
    teams_event_data = TeamsEventData(**event_data)

    # Assert that the instance is created and is of the correct type
    assert isinstance(teams_event_data, TeamsEventData)
    # Optionally, assert that attributes are correctly assigned
    assert teams_event_data.user_name == "user_name"
    assert teams_event_data.event_label == "message"
