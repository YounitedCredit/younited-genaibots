from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from core.backend.enriched_session import EnrichedSession
from core.backend.session_manager_plugin_base import SessionManagerPluginBase


class MockSessionManagerPlugin(SessionManagerPluginBase):
    """Mock implementation of SessionManagerPluginBase for testing"""
    def __init__(self):
        self.sessions = {}
        self._plugin_name = "mock_session_manager"

    def initialize(self, config=None):
        pass

    @property
    def plugin_name(self) -> str:
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, value: str):
        self._plugin_name = value

    def generate_session_id(self, channel_id: str, thread_id: str) -> str:
        return f"{channel_id}_{thread_id}"

    async def create_session(self, channel_id: str, thread_id: str, start_time: Optional[str] = None, enriched: bool = False):
        session = MagicMock(spec=EnrichedSession)
        session.session_id = self.generate_session_id(channel_id, thread_id)
        session.start_time = start_time or datetime.now().isoformat()
        session.messages = []
        self.sessions[session.session_id] = session
        return session

    async def load_session(self, session_id: str) -> Optional[EnrichedSession]:
        return self.sessions.get(session_id)

    async def save_session(self, session: EnrichedSession):
        self.sessions[session.session_id] = session

    async def get_or_create_session(self, channel_id: str, thread_id: str, enriched: bool = False):
        session_id = self.generate_session_id(channel_id, thread_id)
        session = await self.load_session(session_id)
        if not session:
            session = await self.create_session(channel_id, thread_id, enriched=enriched)
        return session

    def append_messages(self, messages: List[Dict], message: Dict, session_id: str):
        messages.append(message)

    async def add_mind_interaction_to_message(self, session, message_index: int, interaction: Dict):
        if 0 <= message_index < len(session.messages):
            if 'mind_interactions' not in session.messages[message_index]:
                session.messages[message_index]['mind_interactions'] = []
            session.messages[message_index]['mind_interactions'].append(interaction)

    async def add_user_interaction_to_message(self, session, message_index: int, interaction: Dict):
        if 0 <= message_index < len(session.messages):
            if 'user_interactions' not in session.messages[message_index]:
                session.messages[message_index]['user_interactions'] = []
            session.messages[message_index]['user_interactions'].append(interaction)

@pytest.fixture
def session_manager():
    return MockSessionManagerPlugin()

def test_plugin_name(session_manager):
    """Test plugin name property"""
    assert session_manager.plugin_name == "mock_session_manager"

    session_manager.plugin_name = "new_name"
    assert session_manager.plugin_name == "new_name"

def test_initialize(session_manager):
    """Test initialize method"""
    config = {"test": "config"}
    session_manager.initialize(config)  # Should not raise any exception

def test_generate_session_id(session_manager):
    """Test session ID generation"""
    session_id = session_manager.generate_session_id("channel1", "thread1")
    assert session_id == "channel1_thread1"
    assert isinstance(session_id, str)

@pytest.mark.asyncio
async def test_create_session(session_manager):
    """Test session creation"""
    start_time = datetime.now().isoformat()
    session = await session_manager.create_session(
        channel_id="channel1",
        thread_id="thread1",
        start_time=start_time
    )

    assert session.session_id == "channel1_thread1"
    assert session.start_time == start_time
    assert session.messages == []

@pytest.mark.asyncio
async def test_load_session(session_manager):
    """Test session loading"""
    # Create a session first
    session = await session_manager.create_session("channel1", "thread1")

    # Test loading existing session
    loaded_session = await session_manager.load_session(session.session_id)
    assert loaded_session == session

    # Test loading non-existent session
    non_existent = await session_manager.load_session("non_existent")
    assert non_existent is None

@pytest.mark.asyncio
async def test_save_session(session_manager):
    """Test session saving"""
    # Create and modify a session
    session = await session_manager.create_session("channel1", "thread1")
    session.messages = [{"content": "test message"}]

    # Save and reload the session
    await session_manager.save_session(session)
    loaded_session = await session_manager.load_session(session.session_id)

    assert loaded_session == session
    assert loaded_session.messages == session.messages

@pytest.mark.asyncio
async def test_get_or_create_session(session_manager):
    """Test get_or_create_session method"""
    # Test creating new session
    session1 = await session_manager.get_or_create_session("channel1", "thread1")
    assert session1.session_id == "channel1_thread1"

    # Test getting existing session
    session2 = await session_manager.get_or_create_session("channel1", "thread1")
    assert session2 == session1

@pytest.mark.asyncio
async def test_append_messages(session_manager):
    """Test message appending"""
    messages = []
    message = {"content": "test message"}

    session_manager.append_messages(messages, message, "session1")
    assert len(messages) == 1
    assert messages[0] == message

@pytest.mark.asyncio
async def test_add_mind_interaction(session_manager):
    """Test adding mind interaction to a message"""
    session = await session_manager.create_session("channel1", "thread1")
    session.messages = [{"content": "test message"}]

    interaction = {"type": "thought", "content": "processing"}

    await session_manager.add_mind_interaction_to_message(session, 0, interaction)

    assert 'mind_interactions' in session.messages[0]
    assert session.messages[0]['mind_interactions'] == [interaction]

    # Test invalid index
    await session_manager.add_mind_interaction_to_message(session, 999, interaction)
    assert len(session.messages) == 1  # Should not modify messages

@pytest.mark.asyncio
async def test_add_user_interaction(session_manager):
    """Test adding user interaction to a message"""
    session = await session_manager.create_session("channel1", "thread1")
    session.messages = [{"content": "test message"}]

    interaction = {"type": "reaction", "content": "👍"}

    # Add first interaction
    await session_manager.add_user_interaction_to_message(session, 0, interaction)
    assert 'user_interactions' in session.messages[0]
    assert session.messages[0]['user_interactions'] == [interaction]

    # Add second interaction
    interaction2 = {"type": "reply", "content": "thanks"}
    await session_manager.add_user_interaction_to_message(session, 0, interaction2)
    assert len(session.messages[0]['user_interactions']) == 2

    # Test invalid index
    await session_manager.add_user_interaction_to_message(session, 999, interaction)
    assert len(session.messages) == 1  # Should not modify messages

@pytest.mark.asyncio
async def test_create_session_with_enriched_flag(session_manager):
    """Test session creation with enriched flag"""
    session = await session_manager.create_session(
        channel_id="channel1",
        thread_id="thread1",
        enriched=True
    )
    assert session.session_id == "channel1_thread1"

@pytest.mark.asyncio
async def test_get_or_create_session_with_enriched_flag(session_manager):
    """Test get_or_create_session with enriched flag"""
    session = await session_manager.get_or_create_session(
        channel_id="channel1",
        thread_id="thread1",
        enriched=True
    )
    assert session.session_id == "channel1_thread1"


import pytest

from core.global_manager import GlobalManager


class TestSessionManagerPluginBase:
    """Test class for SessionManagerPluginBase to verify NotImplementedError"""

    class MockGlobalManager(GlobalManager):
        """Mock class that inherits from GlobalManager"""
        def __init__(self):
            self.logger = MagicMock()
            self.config_manager = MagicMock()
            self.plugin_manager = MagicMock()
            self.session_manager_dispatcher = MagicMock()
            self.user_interactions_dispatcher = MagicMock()
            self.action_interactions_handler = MagicMock()
            self.genai_interactions_text_dispatcher = MagicMock()
            self.genai_interactions_image_dispatcher = MagicMock()
            self.backend_internal_data_processing_dispatcher = MagicMock()
            self.user_interactions_behavior_dispatcher = MagicMock()
            self.prompt_manager = MagicMock()
            self.interaction_queue_manager = MagicMock()

            # Mock the bot_config
            self.bot_config = MagicMock()
            self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING = False

    class MinimalSessionManagerPlugin(SessionManagerPluginBase):
        """Minimal implementation with only abstract methods from PluginBase"""
        def __init__(self, global_manager):
            super().__init__(global_manager)
            self._plugin_name = "minimal_plugin"

        def initialize(self, config=None):
            pass

        @property
        def plugin_name(self) -> str:
            return self._plugin_name

        @plugin_name.setter
        def plugin_name(self, value: str):
            self._plugin_name = value

    @pytest.fixture
    def mock_global_manager(self):
        return self.MockGlobalManager()

    @pytest.fixture
    def base_session_manager(self, mock_global_manager):
        return self.MinimalSessionManagerPlugin(global_manager=mock_global_manager)

    def test_generate_session_id_not_implemented(self, base_session_manager):
        """Test that generate_session_id raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            base_session_manager.generate_session_id("channel1", "thread1")
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_create_session_not_implemented(self, base_session_manager):
        """Test that create_session raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.create_session("channel1", "thread1")
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_load_session_not_implemented(self, base_session_manager):
        """Test that load_session raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.load_session("session1")
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_save_session_not_implemented(self, base_session_manager):
        """Test that save_session raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.save_session(None)
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_add_user_interaction_to_message_not_implemented(self, base_session_manager):
        """Test that add_user_interaction_to_message raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.add_user_interaction_to_message(None, 0, {})
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_get_or_create_session_not_implemented(self, base_session_manager):
        """Test that get_or_create_session raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.get_or_create_session("channel1", "thread1")
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    def test_append_messages_not_implemented(self, base_session_manager):
        """Test that append_messages raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            base_session_manager.append_messages([], {}, "session1")
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_add_mind_interaction_not_implemented(self, base_session_manager):
        """Test that add_mind_interaction_to_message raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.add_mind_interaction_to_message(None, 0, {})
        assert str(exc_info.value) == "This method should be implemented by subclasses"

    @pytest.mark.asyncio
    async def test_add_user_interaction_not_implemented(self, base_session_manager):
        """Test that add_user_interaction_to_message raises NotImplementedError"""
        with pytest.raises(NotImplementedError) as exc_info:
            await base_session_manager.add_user_interaction_to_message(None, 0, {})
        assert str(exc_info.value) == "This method should be implemented by subclasses"
