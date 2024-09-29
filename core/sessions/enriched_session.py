from core.sessions.session_base import SessionBase
import json
from datetime import datetime
from typing import List, Dict, Optional

class EnrichedSession(SessionBase):
    def __init__(self, session_id: str, start_time: Optional[str] = None):
        super().__init__(session_id, start_time)
        self.total_cost = {
            "total_tokens": 0,
            "total_cost": 0.0
        }
        self.total_time_ms = 0.0  # Initialize total_time_ms to track session duration
        self.messages = []  # Initialize messages as an empty list
        self.end_time = None  # Initialize end_time
        # Removed self.actions and self.events since they are not needed at the session level

    def end_session(self) -> None:
        """
        Marks the end of the session and calculates the total time.
        Automatically sets the end_time to the current time.
        """
        self.end_time = datetime.now().isoformat()  # End session at the current time
        self.calculate_total_time()

    def calculate_total_time(self) -> None:
        """
        Calculates the total time of the session in milliseconds.
        """
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.total_time_ms = int((end - start).total_seconds() * 1000)
        except Exception as e:
            print(f"Error calculating total time: {e}")
    
    def accumulate_cost(self, cost: Dict) -> None:
        """
        Accumulates the total cost in terms of tokens and monetary value.
        """
        self.total_cost["total_tokens"] += cost.get("total_tokens", 0)
        self.total_cost["total_cost"] += cost.get("total_cost", 0.0)

    def to_dict(self) -> Dict:
        """
        Converts the session into a dictionary for export or storage.
        """
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_time_ms": self.total_time_ms,
            "total_cost": self.total_cost,
            "messages": self.messages  # Include messages in the session export
            # Removed events and actions from the root level
        }

    @classmethod
    def from_dict(cls, session_data: dict) -> 'EnrichedSession':
        session_id = session_data.get("session_id", "")
        start_time = session_data.get("start_time", "")
        total_cost = session_data.get("total_cost", {"total_tokens": 0, "total_cost": 0.0})
        messages = session_data.get("messages", [])
        total_time_ms = session_data.get("total_time_ms", 0.0)
        end_time = session_data.get("end_time", None)

        # Initialize the session
        enriched_session = cls(session_id, start_time)
        enriched_session.total_cost = total_cost
        enriched_session.messages = messages
        enriched_session.total_time_ms = total_time_ms
        enriched_session.end_time = end_time

        return enriched_session
