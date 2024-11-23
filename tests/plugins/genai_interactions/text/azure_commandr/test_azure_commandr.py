from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.azure_commandr.azure_commandr import (
    AzureCommandrPlugin,
)


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_commandr",
        "AZURE_COMMANDR_INPUT_TOKEN_PRICE": 0.01,
        "AZURE_COMMANDR_OUTPUT_TOKEN_PRICE": 0.01,
        "AZURE_COMMANDR_KEY": "fake_key",
        "AZURE_COMMANDR_ENDPOINT": "https://fake_endpoint",
        "AZURE_COMMANDR_MODELNAME": "commandr-model",
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "AZURE_COMMANDR": mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_commandr_plugin(extended_mock_global_manager):
    plugin = AzureCommandrPlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(azure_commandr_plugin):
    assert azure_commandr_plugin.azure_commandr_key == "fake_key"
    assert azure_commandr_plugin.azure_commandr_endpoint == "https://fake_endpoint"
    assert azure_commandr_plugin.azure_commandr_modelname == "commandr-model"
    assert azure_commandr_plugin.plugin_name == "azure_commandr"

@pytest.mark.asyncio
async def test_handle_action(azure_commandr_plugin):
    with patch.object(azure_commandr_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create, \
         patch.object(azure_commandr_plugin.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(azure_commandr_plugin.session_manager_dispatcher, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(azure_commandr_plugin.session_manager_dispatcher, 'append_messages', new_callable=MagicMock) as mock_append_messages, \
         patch.object(azure_commandr_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:

        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Generated response"))]
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        fake_session = MagicMock()
        fake_session.messages = []
        fake_session.session_id = "test_session_id"
        mock_get_or_create_session.return_value = fake_session

        mock_read_data_content.return_value = "Test prompt content"

        action_input = ActionInput(
            action_name='generate_text',
            parameters={
                'input': 'test input',
                'messages': [],
                'main_prompt': 'test prompt',
                'context': 'test context',
                'conversation_data': 'test conversation'
            }
        )

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

        result = await azure_commandr_plugin.handle_action(action_input, event)
        
        assert result == "Generated response"
        
        # Verify session interactions
        mock_get_or_create_session.assert_called_once()
        mock_append_messages.assert_called()
        mock_save_session.assert_called_once_with(fake_session)

        # Verify completion call
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs['model'] == azure_commandr_plugin.azure_commandr_modelname
        assert call_kwargs['temperature'] == 0.1
        assert call_kwargs['top_p'] == 0.1
        assert isinstance(call_kwargs['messages'], list)
        
@pytest.mark.asyncio
async def test_generate_completion(azure_commandr_plugin):
    messages = [{"role": "user", "content": "Test message"}]
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

    with patch.object(azure_commandr_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Generated response"))]
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        response, genai_cost_base = await azure_commandr_plugin.generate_completion(messages, event)

        assert response == "Generated response"
        assert genai_cost_base.total_tk == 100
        assert genai_cost_base.prompt_tk == 50
        assert genai_cost_base.completion_tk == 50
        assert genai_cost_base.input_token_price == azure_commandr_plugin.input_token_price
        assert genai_cost_base.output_token_price == azure_commandr_plugin.output_token_price

        mock_create.assert_called_once_with(
            model=azure_commandr_plugin.azure_commandr_modelname,
            messages=messages,
            temperature=0.1,
            top_p=0.1,
        )

@pytest.mark.asyncio
async def test_trigger_genai(azure_commandr_plugin):
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

    with patch.object(azure_commandr_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_commandr_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_commandr_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', MagicMock(return_value="<@BOT123> user text")) as mock_format_message:

        await azure_commandr_plugin.trigger_genai(event)

        # Vérifier que format_trigger_genai_message a été appelé avec les bons arguments
        mock_format_message.assert_called_once_with(event=event, message="user text")

        assert mock_send_message.call_count == 2
        mock_send_message.assert_any_call(event=event, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)
        mock_send_message.assert_any_call(
            event=event,
            message=":zap::robot_face: *AutomatedUserInput*: <@BOT123> user text",
            message_type=MessageType.TEXT,
            is_internal=True
        )

        mock_process.assert_called_once_with(event)

        # Vérifier que les attributs de l'événement ont été correctement modifiés
        assert event.user_id == "AUTOMATED_RESPONSE"
        assert event.user_name == "AUTOMATED_RESPONSE"
        assert event.user_email == "AUTOMATED_RESPONSE"
        assert event.event_label == "thread_message"
        assert event.text == "<@BOT123> user text"
        assert event.is_mention == True
        assert event.thread_id == "thread_id"
