from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.user_interactions_behaviors.custom_api.ca_default_behavior.ca_default_behavior import (
    CaDefaultBehaviorPlugin,
)


class TestCaDefaultBehaviorPlugin(CaDefaultBehaviorPlugin):
    async def begin_genai_completion(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        await self.update_reaction(event, channel_id, timestamp, remove_reaction=self.reaction_writing, add_reaction=self.reaction_generating)

    async def end_genai_completion(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        await self.update_reaction(event, channel_id, timestamp, remove_reaction=self.reaction_generating)

    async def begin_long_action(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        pass

    async def end_long_action(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        pass

    async def begin_wait_backend(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        pass

    async def end_wait_backend(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        pass

    async def mark_error(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        pass

@pytest.fixture
def global_manager(mock_global_manager):
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    mock_global_manager.bot_config = MagicMock()
    mock_global_manager.bot_config.BREAK_KEYWORD = "break"
    mock_global_manager.bot_config.START_KEYWORD = "start"
    return mock_global_manager

@pytest.fixture
def ca_default_behavior_plugin(global_manager):
    plugin = TestCaDefaultBehaviorPlugin(global_manager)
    plugin.initialize()
    plugin.custom_api_plugin = MagicMock()  # Changez AsyncMock en MagicMock
    plugin.custom_api_plugin.reactions = MagicMock()
    plugin.custom_api_plugin.reactions.PROCESSING = "processing"
    plugin.custom_api_plugin.reactions.DONE = "done"
    plugin.custom_api_plugin.reactions.ACKNOWLEDGE = "acknowledge"
    plugin.custom_api_plugin.reactions.GENERATING = "generating"
    plugin.custom_api_plugin.reactions.WRITING = "writing"
    plugin.custom_api_plugin.reactions.ERROR = "error"
    plugin.custom_api_plugin.reactions.WAIT = "wait"
    plugin.reaction_done = plugin.custom_api_plugin.reactions.DONE
    plugin.reaction_writing = plugin.custom_api_plugin.reactions.WRITING
    plugin.reaction_generating = plugin.custom_api_plugin.reactions.GENERATING
    plugin.reaction_processing = plugin.custom_api_plugin.reactions.PROCESSING
    plugin.reaction_acknowledge = plugin.custom_api_plugin.reactions.ACKNOWLEDGE
    plugin.reaction_error = plugin.custom_api_plugin.reactions.ERROR
    return plugin

@pytest.mark.asyncio
async def test_initialize(ca_default_behavior_plugin, global_manager):
    ca_default_behavior_plugin.initialize()
    assert ca_default_behavior_plugin.user_interactions_dispatcher == global_manager.user_interactions_dispatcher
    assert ca_default_behavior_plugin.genai_interactions_text_dispatcher == global_manager.genai_interactions_text_dispatcher
    assert ca_default_behavior_plugin.backend_internal_data_processing_dispatcher == global_manager.backend_internal_data_processing_dispatcher

def test_plugin_name_getter(ca_default_behavior_plugin):
    assert ca_default_behavior_plugin.plugin_name == "ca_default_behavior"

def test_plugin_name_setter(ca_default_behavior_plugin):
    ca_default_behavior_plugin.plugin_name = "new_plugin_name"
    assert ca_default_behavior_plugin.plugin_name == "new_plugin_name"

@pytest.mark.asyncio
async def test_process_interaction_none_event(ca_default_behavior_plugin):
    ca_default_behavior_plugin.logger = MagicMock()
    await ca_default_behavior_plugin.process_interaction(None)
    ca_default_behavior_plugin.logger.debug.assert_called_with("No event")

@pytest.mark.asyncio
async def test_update_reaction(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"
    ca_default_behavior_plugin.user_interactions_dispatcher = AsyncMock()

    await ca_default_behavior_plugin.update_reaction(event, "C123", "1234567890.123456", "old_reaction", "new_reaction")
    ca_default_behavior_plugin.user_interactions_dispatcher.remove_reaction.assert_awaited_with(channel_id="C123", timestamp="1234567890.123456", reaction_name="old_reaction")
    ca_default_behavior_plugin.user_interactions_dispatcher.add_reaction.assert_awaited_with(channel_id="C123", timestamp="1234567890.123456", reaction_name="new_reaction")

@pytest.mark.asyncio
async def test_process_incoming_notification_data(ca_default_behavior_plugin, global_manager):
    event = AsyncMock()
    event.channel_id = "C123"
    event.timestamp = "1234567890.123456"
    event.event_label = "message"
    event.is_mention = True
    event.to_dict = MagicMock(return_value={"key": "value"})  # Mock to_dict

    global_manager.bot_config.REQUIRE_MENTION_NEW_MESSAGE = True
    global_manager.genai_interactions_text_dispatcher.handle_request = AsyncMock(return_value='{"some": "json"}')
    global_manager.action_interactions_handler.handle_request = AsyncMock()

    ca_default_behavior_plugin.logger = MagicMock()

    await ca_default_behavior_plugin.process_incoming_notification_data(event)

@pytest.mark.asyncio
async def test_begin_genai_completion(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    ca_default_behavior_plugin.update_reaction = AsyncMock()

    await ca_default_behavior_plugin.begin_genai_completion(event, "C123", "1234567890.123456")

    ca_default_behavior_plugin.update_reaction.assert_awaited_with(
        event,
        "C123",
        "1234567890.123456",
        remove_reaction=ca_default_behavior_plugin.reaction_writing,
        add_reaction=ca_default_behavior_plugin.reaction_generating
    )

@pytest.mark.asyncio
async def test_end_genai_completion(ca_default_behavior_plugin):
    event = AsyncMock(IncomingNotificationDataBase)
    ca_default_behavior_plugin.update_reaction = AsyncMock()

    await ca_default_behavior_plugin.end_genai_completion(event, "C123", "1234567890.123456")

    ca_default_behavior_plugin.update_reaction.assert_awaited_with(
        event,
        "C123",
        "1234567890.123456",
        remove_reaction=ca_default_behavior_plugin.reaction_generating
    )

@pytest.mark.asyncio
async def test_process_interaction_break_keyword(ca_default_behavior_plugin, global_manager):
    event = AsyncMock(IncomingNotificationDataBase)
    event.event_label = "thread_message"
    event.text = global_manager.bot_config.BREAK_KEYWORD
    event.channel_id = "C123"
    event.thread_id = "T456"
    event.timestamp = "1234567890.123456"
    ca_default_behavior_plugin.user_interactions_dispatcher.request_to_notification_data = AsyncMock(return_value=event)

    # Créez un mock pour custom_api_plugin
    mock_custom_api_plugin = AsyncMock()
    mock_custom_api_plugin.reactions = MagicMock()
    mock_custom_api_plugin.reactions.PROCESSING = "processing"
    mock_custom_api_plugin.reactions.DONE = "done"
    mock_custom_api_plugin.reactions.ACKNOWLEDGE = "acknowledge"
    mock_custom_api_plugin.reactions.GENERATING = "generating"
    mock_custom_api_plugin.reactions.WRITING = "writing"
    mock_custom_api_plugin.reactions.ERROR = "error"
    mock_custom_api_plugin.reactions.WAIT = "wait"
    mock_custom_api_plugin.add_reaction = AsyncMock()

    ca_default_behavior_plugin.user_interactions_dispatcher.get_plugin = AsyncMock(return_value=mock_custom_api_plugin)

    await ca_default_behavior_plugin.process_interaction(event)

    # Ajoutez vos assertions ici
    ca_default_behavior_plugin.user_interactions_dispatcher.send_message.assert_called()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_called()

@pytest.mark.asyncio
async def test_process_interaction_start_keyword(ca_default_behavior_plugin, global_manager):
    event = AsyncMock(IncomingNotificationDataBase)
    event.event_label = "thread_message"
    event.text = global_manager.bot_config.START_KEYWORD
    event.channel_id = "C123"
    event.thread_id = "T456"
    event.timestamp = "1234567890.123456"  # Ajoutez ceci
    ca_default_behavior_plugin.user_interactions_dispatcher.request_to_notification_data = AsyncMock(return_value=event)

    mock_custom_api_plugin = AsyncMock()
    mock_custom_api_plugin.reactions = MagicMock()
    mock_custom_api_plugin.reactions.PROCESSING = "processing"
    mock_custom_api_plugin.reactions.DONE = "done"
    mock_custom_api_plugin.reactions.ACKNOWLEDGE = "acknowledge"
    mock_custom_api_plugin.reactions.GENERATING = "generating"
    mock_custom_api_plugin.reactions.WRITING = "writing"
    mock_custom_api_plugin.reactions.ERROR = "error"
    mock_custom_api_plugin.reactions.WAIT = "wait"
    mock_custom_api_plugin.add_reaction = AsyncMock()

    ca_default_behavior_plugin.user_interactions_dispatcher.get_plugin = AsyncMock(return_value=mock_custom_api_plugin)

    await ca_default_behavior_plugin.process_interaction(event)

    ca_default_behavior_plugin.user_interactions_dispatcher.send_message.assert_called()
    ca_default_behavior_plugin.backend_internal_data_processing_dispatcher.remove_data_content.assert_called()

@pytest.mark.asyncio
async def test_process_interaction_error(ca_default_behavior_plugin, global_manager):
    event = AsyncMock(IncomingNotificationDataBase)
    ca_default_behavior_plugin.user_interactions_dispatcher.request_to_notification_data.side_effect = Exception("Test error")

    # Créez un mock pour custom_api_plugin
    mock_custom_api_plugin = MagicMock()
    mock_custom_api_plugin.reactions.PROCESSING = "processing"
    ca_default_behavior_plugin.user_interactions_dispatcher.get_plugin = AsyncMock(return_value=mock_custom_api_plugin)

    with pytest.raises(Exception):
        await ca_default_behavior_plugin.process_interaction(event)

    ca_default_behavior_plugin.user_interactions_dispatcher.send_message.assert_called_with(
        event=event,
        message=ANY,
        message_type=MessageType.TEXT,
        is_internal=True,
        show_ref=False
    )
