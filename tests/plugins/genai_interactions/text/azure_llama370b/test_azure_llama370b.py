import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.azure_llama370b.azure_llama370b import (
    AzureLlama370bPlugin,
)


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_llama370b",
        "AZURE_LLAMA370B_INPUT_TOKEN_PRICE": 0.01,
        "AZURE_LLAMA370B_OUTPUT_TOKEN_PRICE": 0.01,
        "AZURE_LLAMA370B_KEY": "fake_key",
        "AZURE_LLAMA370B_ENDPOINT": "https://fake_endpoint",
        "AZURE_LLAMA370B_MODELNAME": "llama370b-model",
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "AZURE_LLAMA370B": mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_llama370b_plugin(extended_mock_global_manager):
    plugin = AzureLlama370bPlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(azure_llama370b_plugin):
    assert azure_llama370b_plugin.azure_llama370b_key == "fake_key"
    assert azure_llama370b_plugin.azure_llama370b_endpoint == "https://fake_endpoint"
    assert azure_llama370b_plugin.azure_llama370b_modelname == "llama370b-model"
    assert azure_llama370b_plugin.plugin_name == "azure_llama370b"

@pytest.mark.asyncio
async def test_handle_action_with_empty_blob(azure_llama370b_plugin):
    with patch.object(azure_llama370b_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create, \
         patch.object(azure_llama370b_plugin.session_manager, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(azure_llama370b_plugin.session_manager, 'add_event_to_session', new_callable=AsyncMock) as mock_add_event_to_session, \
         patch.object(azure_llama370b_plugin.session_manager, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(azure_llama370b_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(azure_llama370b_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
         patch.object(azure_llama370b_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        mock_get_or_create_session.return_value = MagicMock()
        mock_read_data_content.return_value = ""

        action_input = ActionInput(action_name='generate_text', parameters={'input': 'test input', 'main_prompt': 'test prompt', 'context': 'test context', 'conversation_data': 'test conversation'})
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
            origin_plugin_name="origin_plugin_name"
        )

        result = await azure_llama370b_plugin.handle_action(action_input, event)
        assert result == "Generated response"
        
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['model'] == "llama370b-model"
        assert call_kwargs['temperature'] == 0.1
        assert call_kwargs['top_p'] == 0.1
        assert len(call_kwargs['messages']) == 4
        assert call_kwargs['messages'][0] == {"role": "system", "content": ""}
        assert call_kwargs['messages'][1]['role'] == "user"
        assert "Here is additional context relevant to the following request: test context" in call_kwargs['messages'][1]['content']
        assert call_kwargs['messages'][2]['role'] == "user"
        assert "Here is the conversation that led to the following request:``` test conversation ```" in call_kwargs['messages'][2]['content']
        assert call_kwargs['messages'][3] == {"role": "user", "content": "test input"}

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(azure_llama370b_plugin):
    with patch.object(azure_llama370b_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create, \
         patch.object(azure_llama370b_plugin.session_manager, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(azure_llama370b_plugin.session_manager, 'add_event_to_session', new_callable=AsyncMock) as mock_add_event_to_session, \
         patch.object(azure_llama370b_plugin.session_manager, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(azure_llama370b_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(azure_llama370b_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
         patch.object(azure_llama370b_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        mock_get_or_create_session.return_value = MagicMock()

        existing_messages = [{"role": "assistant", "content": "previous message"}]
        mock_read_data_content.return_value = json.dumps(existing_messages)

        action_input = ActionInput(action_name='generate_text', parameters={'input': 'test input', 'main_prompt': 'test prompt', 'context': 'test context', 'conversation_data': 'test conversation'})
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
            origin_plugin_name="origin_plugin_name"
        )

        result = await azure_llama370b_plugin.handle_action(action_input, event)
        assert result == "Generated response"
        
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['model'] == "llama370b-model"
        assert call_kwargs['temperature'] == 0.1
        assert call_kwargs['top_p'] == 0.1
        assert len(call_kwargs['messages']) == 4
        assert call_kwargs['messages'][0] == {"role": "system", "content": json.dumps(existing_messages)}
        assert call_kwargs['messages'][1]['role'] == "user"
        assert "Here is additional context relevant to the following request: test context" in call_kwargs['messages'][1]['content']
        assert call_kwargs['messages'][2]['role'] == "user"
        assert "Here is the conversation that led to the following request:``` test conversation ```" in call_kwargs['messages'][2]['content']
        assert call_kwargs['messages'][3] == {"role": "user", "content": "test input"}
        
@pytest.mark.asyncio
async def test_trigger_genai_long_text(azure_llama370b_plugin):
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

    with patch.object(azure_llama370b_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_llama370b_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_llama370b_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', mock_format_trigger_genai_message), \
         patch.object(azure_llama370b_plugin.user_interaction_dispatcher, 'upload_file', new_callable=AsyncMock) as mock_upload_file:

        await azure_llama370b_plugin.trigger_genai(event)

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
