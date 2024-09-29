import json
from datetime import datetime
from core.sessions.enriched_session import EnrichedSession
from core.sessions.session_base import SessionBase
from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from core.global_manager import GlobalManager  # Forward reference to avoid circular import

class SessionManager:
    def __init__(self, global_manager: 'GlobalManager'):
        self.global_manager = global_manager
        self.backend_dispatcher = None
        self.logger = global_manager.logger
        self.sessions = {}  # Initialize the sessions dictionary

    def initialize(self):
        """
        Initializes the session manager, setting the backend dispatcher from the global manager.
        """
        self.backend_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    def generate_session_id(self, channel_id: str, thread_id: str) -> str:
        return f"{channel_id}_{thread_id}.json"

    async def create_session(self, channel_id: str, thread_id: str, start_time: Optional[str] = None, enriched: bool = False):
        session_id = self.generate_session_id(channel_id, thread_id)
        if enriched:
            return EnrichedSession(session_id, start_time)
        else:
            return SessionBase(session_id, start_time)
        
    async def load_session(self, session_id: str) -> Optional[EnrichedSession]:
        session_json = await self.backend_dispatcher.read_data_content(
            self.backend_dispatcher.sessions, session_id
        )
        if session_json:
            session_data = json.loads(session_json)
            session = EnrichedSession.from_dict(session_data)
            self.sessions[session_id] = session
            return session
        else:
            return None

    async def save_session(self, session: EnrichedSession):
        session_data = session.to_dict()
        session_json = json.dumps(session_data, default=str)
        await self.backend_dispatcher.write_data_content(
            self.backend_dispatcher.sessions, session.session_id, session_json
        )

    async def add_user_interaction_to_message(self, session: EnrichedSession, message_index: int, interaction: Dict):
        """
        Adds a user interaction to a specific message in the session.
        This method now ensures that the interaction is placed within the correct assistant message.
        """
        session.add_user_interaction_to_message(message_index, interaction)
        await self.save_session(session)

    async def get_or_create_session(self, channel_id: str, thread_id: str, enriched: bool = False):
        session_id = self.generate_session_id(channel_id, thread_id)
        if session_id in self.sessions:
            return self.sessions[session_id]
        else:
            # Try to load the session from the backend
            session = await self.load_session(session_id)
            if session:
                self.sessions[session_id] = session
                return session
            else:
                # Create a new session
                start_time = datetime.now().isoformat()
                session = await self.create_session(channel_id, thread_id, start_time, enriched)
                self.sessions[session_id] = session
                return session
