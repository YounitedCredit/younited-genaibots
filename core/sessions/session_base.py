import json
from typing import List, Dict, Optional
from datetime import datetime

class SessionBase:
    def __init__(self, session_id: str, start_time: Optional[str] = None):
        """
        Base class for managing sessions.
        """
        self.session_id = session_id
        self.start_time = start_time or datetime.now().isoformat()
        self.end_time = None
        self.events: List[Dict] = []

    def add_event(self, event_type: str, data: Dict) -> None:
        """
        Adds an event to the session.
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)

    def end_session(self, end_time: Optional[str] = None) -> None:
        """
        Ends the session and marks the end time.
        """
        self.end_time = end_time or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """
        Converts the session into a dictionary ready for JSON storage.
        """
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "events": self.events
        }

    def to_json(self) -> str:
        """
        Converts the session into a JSON string.
        """
        return json.dumps(self.to_dict(), indent=2)
