class QueuedInteraction:
    def __init__(self, event_type: str, event: dict, **kwargs):
        self.event_type = event_type  # Function name like 'send_message', 'add_reaction', etc.
        self.event = event  # The event data itself
        self.params = kwargs  # Additional parameters for the function call

    def to_dict(self) -> dict:
        """Convert to a dictionary for serialization"""
        return {
            "event_type": self.event_type,
            "event": self.event,
            "params": self.params
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Reconstruct from a dictionary"""
        return cls(
            event_type=data["event_type"],
            event=data["event"],
            **data["params"]
        )
