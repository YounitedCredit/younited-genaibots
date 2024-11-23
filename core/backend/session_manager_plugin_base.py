import json
from datetime import datetime
from typing import Dict, List, Optional
from core.plugin_base import PluginBase
from core.backend.enriched_session import EnrichedSession

class SessionManagerPluginBase(PluginBase):
    def generate_session_id(self, channel_id: str, thread_id: str) -> str:
        raise NotImplementedError("This method should be implemented by subclasses")

    async def create_session(self, channel_id: str, thread_id: str, start_time: Optional[str] = None, enriched: bool = False):
        raise NotImplementedError("This method should be implemented by subclasses")

    async def load_session(self, session_id: str) -> Optional[EnrichedSession]: # type: ignore
        raise NotImplementedError("This method should be implemented by subclasses")

    async def save_session(self, session: EnrichedSession):
        raise NotImplementedError("This method should be implemented by subclasses")

    async def add_user_interaction_to_message(self, session: EnrichedSession, message_index: int, interaction: Dict):
        raise NotImplementedError("This method should be implemented by subclasses")

    async def get_or_create_session(self, channel_id: str, thread_id: str, enriched: bool = False):
        raise NotImplementedError("This method should be implemented by subclasses")
    
    def append_messages(self, messages: List[Dict], message: Dict, session_id: str):
        raise NotImplementedError("This method should be implemented by subclasses")
    
    async def add_mind_interaction_to_message(self, session, message_index: int, interaction: Dict) -> None:
        """
        Add a mind interaction to a specific assistant message by index.
        This interaction is stored inside the specific assistant message.
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    async def add_user_interaction_to_message(self, session, message_index: int, interaction: Dict) -> None:
        """
        Add a user interaction to a specific assistant message by index.
        This interaction is stored inside the specific assistant message.
        """
        raise NotImplementedError("This method should be implemented by subclasses")