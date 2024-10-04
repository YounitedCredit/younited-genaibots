from core.event_processing.queued_interaction import QueuedInteraction


# Test for the initialization of QueuedInteraction
def test_queued_interaction_initialization():
    event_type = "send_message"
    event = {"message": "Hello"}
    params = {"param1": "value1", "param2": "value2"}

    # Create instance of QueuedInteraction
    interaction = QueuedInteraction(event_type=event_type, event=event, **params)

    # Assert that the object is initialized correctly
    assert interaction.event_type == event_type
    assert interaction.event == event
    assert interaction.params == params

# Test for converting QueuedInteraction to dictionary
def test_queued_interaction_to_dict():
    event_type = "send_message"
    event = {"message": "Hello"}
    params = {"param1": "value1", "param2": "value2"}

    # Create instance of QueuedInteraction
    interaction = QueuedInteraction(event_type=event_type, event=event, **params)

    # Convert the interaction to a dictionary
    interaction_dict = interaction.to_dict()

    # Assert the dictionary is correctly formed
    assert interaction_dict == {
        "event_type": event_type,
        "event": event,
        "params": params
    }

# Test for creating QueuedInteraction from dictionary
def test_queued_interaction_from_dict():
    data = {
        "event_type": "send_message",
        "event": {"message": "Hello"},
        "params": {"param1": "value1", "param2": "value2"}
    }

    # Create an instance of QueuedInteraction using from_dict
    interaction = QueuedInteraction.from_dict(data)

    # Assert the object is created correctly from the dictionary
    assert interaction.event_type == data["event_type"]
    assert interaction.event == data["event"]
    assert interaction.params == data["params"]

# Test for round-trip serialization (to_dict and from_dict)
def test_queued_interaction_round_trip():
    event_type = "send_message"
    event = {"message": "Hello"}
    params = {"param1": "value1", "param2": "value2"}

    # Create instance of QueuedInteraction
    interaction = QueuedInteraction(event_type=event_type, event=event, **params)

    # Convert to dictionary and back to object
    interaction_dict = interaction.to_dict()
    new_interaction = QueuedInteraction.from_dict(interaction_dict)

    # Assert the new object matches the original
    assert new_interaction.event_type == interaction.event_type
    assert new_interaction.event == interaction.event
    assert new_interaction.params == interaction.params
