import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.azure_mistral.azure_mistral import (
    AzureMistralPlugin,
)


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_mistral",
        "AZURE_MISTRAL_INPUT_TOKEN_PRICE": 0.01,
        "AZURE_MISTRAL_OUTPUT_TOKEN_PRICE": 0.01,
        "AZURE_MISTRAL_KEY": "fake_key",
        "AZURE_MISTRAL_ENDPOINT": "https://fake_endpoint",
        "AZURE_MISTRAL_MODELNAME": "mistral-xxl",
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "AZURE_MISTRAL": mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_mistral_plugin(extended_mock_global_manager):
    plugin = AzureMistralPlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(azure_mistral_plugin):
    assert azure_mistral_plugin.azure_mistral_key == "fake_key"
    assert azure_mistral_plugin.azure_mistral_endpoint == "https://fake_endpoint"
    assert azure_mistral_plugin.azure_mistral_modelname == "mistral-xxl"
    assert azure_mistral_plugin.plugin_name == "azure_mistral"

@pytest.mark.asyncio
async def test_handle_action_with_empty_blob(azure_mistral_plugin):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated response"))]
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
    
    session_mock = MagicMock()
    session_mock.messages = []
    session_mock.session_id = "test_session_id"
    
    with patch.object(azure_mistral_plugin.mistral_client, 'chat', return_value=mock_response) as mock_chat, \
         patch.object(azure_mistral_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(azure_mistral_plugin.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_session:

        mock_read_data_content.return_value = ""
        mock_get_session.return_value = session_mock
        
        action_input = ActionInput(action_name='generate_text', parameters={
            'input': 'test input',
            'main_prompt': 'test prompt',
            'context': 'test context',
            'conversation_data': 'test conversation'
        })
        
        event = IncomingNotificationDataBase(
            channel_id="channel_id", thread_id="thread_id", user_id="user_id",
            text="user text", timestamp="timestamp", event_label="event_label",
            response_id="response_id", user_name="user_name", user_email="user_email",
            is_mention=True, origin_plugin_name="origin_plugin_name"
        )

        result = await azure_mistral_plugin.handle_action(action_input, event)
        
        assert result == "Generated response"
        expected_messages = []
        assert mock_chat.call_args.kwargs['messages'] == expected_messages

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(azure_mistral_plugin):
    existing_messages = [{"role": "assistant", "content": "previous message"}]
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated response"))]
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
    
    session_mock = MagicMock()
    session_mock.messages = existing_messages
    session_mock.session_id = "test_session_id"
    
    with patch.object(azure_mistral_plugin.mistral_client, 'chat', return_value=mock_response) as mock_chat, \
         patch.object(azure_mistral_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(azure_mistral_plugin.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_session:

        mock_read_data_content.return_value = json.dumps(existing_messages)
        mock_get_session.return_value = session_mock
        
        action_input = ActionInput(action_name='generate_text', parameters={
            'input': 'test input',
            'main_prompt': 'test prompt',
            'context': 'test context',
            'conversation_data': 'test conversation'
        })
        
        event = IncomingNotificationDataBase(
            channel_id="channel_id", thread_id="thread_id", user_id="user_id",
            text="user text", timestamp="timestamp", event_label="event_label",
            response_id="response_id", user_name="user_name", user_email="user_email",
            is_mention=True, origin_plugin_name="origin_plugin_name"
        )

        result = await azure_mistral_plugin.handle_action(action_input, event)
        
        assert result == "Generated response"
        expected_messages = []
        assert mock_chat.call_args.kwargs['messages'] == expected_messages
        
@pytest.mark.asyncio
async def test_trigger_genai(azure_mistral_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",

        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin_plugin_name="test_plugin"
    )

    mock_format_trigger_genai_message = MagicMock(return_value="<@BOT123> user text")

    with patch.object(azure_mistral_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_mistral_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_mistral_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', mock_format_trigger_genai_message):

        await azure_mistral_plugin.trigger_genai(event)

        # Verifications
        assert mock_send_message.call_count == 2
        mock_send_message.assert_any_call(event=event, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)
        mock_send_message.assert_any_call(
            event=event,
            message=":zap::robot_face: *AutomatedUserInput*: <@BOT123> user text",
            message_type=MessageType.TEXT,
            is_internal=True
        )

        mock_process.assert_called_once()
        mock_format_trigger_genai_message.assert_called_once_with(event=event, message="user text")

        # Correct the assertions to match the expected uppercase values in the event
        assert event.user_id == "AUTOMATED_RESPONSE"
        assert event.user_name == "AUTOMATED_RESPONSE"
        assert event.user_email == "AUTOMATED_RESPONSE"
        assert event.event_label == "thread_message"
        assert event.text == "<@BOT123> user text"
        assert event.is_mention is True
        assert event.thread_id == "thread_id"


@pytest.mark.asyncio
async def test_trigger_genai_long_text(azure_mistral_plugin):
    long_text = " ".join(["word" for _ in range(301)])  # 301 mots
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text=long_text,
        timestamp="timestamp",

        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin_plugin_name="test_plugin"
    )

    mock_format_trigger_genai_message = MagicMock(return_value=f"<@BOT123> {long_text}")

    with patch.object(azure_mistral_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_mistral_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_mistral_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', mock_format_trigger_genai_message), \
         patch.object(azure_mistral_plugin.user_interaction_dispatcher, 'upload_file', new_callable=AsyncMock) as mock_upload_file:

        await azure_mistral_plugin.trigger_genai(event)

        # Vérifications
        mock_send_message.assert_called_once_with(event=event, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)
        mock_upload_file.assert_called_once_with(
            event=event,
            file_content=f"<@BOT123> {long_text}",
            filename="Bot reply.txt",
            title=":zap::robot_face: Automated User Input",
            is_internal=True
        )

        mock_process.assert_called_once()
        mock_format_trigger_genai_message.assert_called_once_with(event=event, message=long_text)
