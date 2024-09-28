import json
from typing import List, Dict, Optional
from datetime import datetime

class SessionBase:
    def __init__(self, session_id: str, core_prompt: str, main_prompt: str, start_time: Optional[str] = None):
        """
        Classe de base pour gérer les sessions.
        """
        self.session_id = session_id
        self.core_prompt = core_prompt
        self.main_prompt = main_prompt
        self.start_time = start_time or datetime.now().isoformat()
        self.end_time = None
        self.events: List[Dict] = []

    def add_event(self, event_type: str, data: Dict) -> None:
        """
        Ajoute un événement à la session.
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)

    def end_session(self, end_time: Optional[str] = None) -> None:
        """
        Termine la session et marque l'heure de fin.
        """
        self.end_time = end_time or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """
        Convertit la session en dictionnaire prêt à être stocké en JSON.
        """
        return {
            "session_id": self.session_id,
            "core_prompt": self.core_prompt,
            "main_prompt": self.main_prompt,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "events": self.events
        }

    def to_json(self) -> str:
        """
        Convertit la session en chaîne JSON.
        """
        return json.dumps(self.to_dict(), indent=2)
