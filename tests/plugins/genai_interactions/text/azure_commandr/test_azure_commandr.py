import json
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest

from core.action_interactions.action_input import ActionInput
from plugins import IncomingNotificationDataBase
from plugins.genai_interactions.text.azure_commandr.azure_commandr import (
    AzureCommandrPlugin,
)
from core.user_interactions.message_type import MessageType

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
async def test_handle_action_with_empty_blob(azure_commandr_plugin):
    with patch.object(azure_commandr_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(azure_commandr_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(azure_commandr_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(azure_commandr_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

            # Simulate empty blob
            mock_read_data_content.return_value = ""

            action_input = ActionInput(action_name='generate_text', parameters={'input': 'test input', 'main_prompt': 'test prompt', 'context': 'test context', 'conversation_data': 'test conversation'})
            event = IncomingNotificationDataBase(
                channel_id="channel_id",
                thread_id="thread_id",
                user_id="user_id",
                text="user text",
                timestamp="timestamp",
                converted_timestamp="converted_timestamp",
                event_label="event_label",
                response_id="response_id",
                user_name="user_name",
                user_email="user_email",
                is_mention=True,
                origin="origin"
            )

            result = await azure_commandr_plugin.handle_action(action_input, event)
            assert result == "Generated response"
            mock_create.assert_called_once_with(
                model="commandr-model",
                temperature=0.1,
                top_p=0.1,
                messages=[
                    {"role": "system", "content": ""},
                    {"role": "user", "content": "Here is aditionnal context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request:``` test conversation ```"},
                    {"role": "user", "content": "test input"}
                ]
            )
            mock_write_data_content.assert_called_once()
            mock_calculate_and_update_costs.assert_called_once()

            # Verify that the new message is appended to the existing ones
            expected_messages = [{"role": "assistant", "content": "Generated response"}]
            mock_write_data_content.assert_called_with(
                azure_commandr_plugin.backend_internal_data_processing_dispatcher.sessions,
                f"{event.channel_id}-{event.thread_id or event.timestamp}.txt",
                json.dumps(expected_messages)
            )

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(azure_commandr_plugin):
    with patch.object(azure_commandr_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(azure_commandr_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(azure_commandr_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(azure_commandr_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

            # Simulate existing blob content
            existing_messages = [{"role": "assistant", "content": "previous message"}]
            mock_read_data_content.return_value = json.dumps(existing_messages)

            action_input = ActionInput(action_name='generate_text', parameters={'input': 'test input', 'main_prompt': 'test prompt', 'context': 'test context', 'conversation_data': 'test conversation'})
            event = IncomingNotificationDataBase(
                channel_id="channel_id",
                thread_id="thread_id",
                user_id="user_id",
                text="user text",
                timestamp="timestamp",
                converted_timestamp="converted_timestamp",
                event_label="event_label",
                response_id="response_id",
                user_name="user_name",
                user_email="user_email",
                is_mention=True,
                origin="origin"
            )

            result = await azure_commandr_plugin.handle_action(action_input, event)
            assert result == "Generated response"
            mock_create.assert_called_once_with(
                model="commandr-model",
                temperature=0.1,
                top_p=0.1,
                messages=[
                    {"role": "system", "content": json.dumps(existing_messages)},
                    {"role": "user", "content": "Here is aditionnal context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request:``` test conversation ```"},
                    {"role": "user", "content": "test input"}
                ]
            )
            mock_write_data_content.assert_called_once()
            mock_calculate_and_update_costs.assert_called_once()

            # Verify that the new message is appended to the existing ones
            expected_messages = existing_messages + [{"role": "assistant", "content": "Generated response"}]
            mock_write_data_content.assert_called_with(
                azure_commandr_plugin.backend_internal_data_processing_dispatcher.sessions,
                f"{event.channel_id}-{event.thread_id or event.timestamp}.txt",
                json.dumps(expected_messages)
            )

def test_validate_request(azure_commandr_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        converted_timestamp="converted_timestamp",
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin"
    )
    assert azure_commandr_plugin.validate_request(event) == True

@pytest.mark.asyncio
async def test_handle_request(azure_commandr_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        converted_timestamp="converted_timestamp",
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin"
    )
    with patch.object(azure_commandr_plugin.input_handler, 'handle_event_data', new_callable=AsyncMock) as mock_handle_event_data:
        mock_handle_event_data.return_value = "Mocked response"
        response = await azure_commandr_plugin.handle_request(event)
        assert response == "Mocked response"
        mock_handle_event_data.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_generate_completion(azure_commandr_plugin):
    messages = [{"role": "user", "content": "Test message"}]
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        converted_timestamp="converted_timestamp",
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin"
    )
    with patch.object(azure_commandr_plugin.commandr_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        
        response, genai_cost_base = await azure_commandr_plugin.generate_completion(messages, event)
        
        assert response == "Generated response"
        assert genai_cost_base.total_tk == 100
        assert genai_cost_base.prompt_tk == 50
        assert genai_cost_base.completion_tk == 50
        assert genai_cost_base.input_token_price == azure_commandr_plugin.input_token_price
        assert genai_cost_base.output_token_price == azure_commandr_plugin.output_token_price

@pytest.mark.asyncio
async def test_trigger_genai(azure_chatgpt_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        converted_timestamp="converted_timestamp",
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin",
        origin_plugin_name="test_plugin"
    )

    def mock_format_trigger_genai_message(event, message, plugin_name=None):
        return f"<@BOT123> {message}"

    with patch.object(azure_chatgpt_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_chatgpt_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_chatgpt_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', side_effect=mock_format_trigger_genai_message):

        await azure_chatgpt_plugin.trigger_genai(event)

        # Vérifications
        assert mock_send_message.call_count == 2
        mock_send_message.assert_any_call(event=ANY, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)
        mock_send_message.assert_any_call(
            event=ANY, 
            message=":zap::robot_face: *AutomatedUserInput*: <@BOT123> user text", 
            message_type=MessageType.TEXT, 
            is_internal=True
        )
        
        mock_process.assert_called_once()
        
        # Vérifiez que les attributs de l'événement ont été correctement modifiés
        assert event.user_id == "automated response"
        assert event.user_name == "automated response"
        assert event.user_email == "automated response"
        assert event.event_label == "thread_message"
        assert event.text == "<@BOT123> user text"
        assert event.is_mention == True
        assert event.thread_id == "thread_id"

@pytest.mark.asyncio
async def test_trigger_genai(azure_commandr_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        converted_timestamp="converted_timestamp",
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin",
        origin_plugin_name="test_plugin"
    )

    async def mock_send_message(event, message, message_type, is_internal=False):
        print(f"mock_send_message called with message: {message}")

    async def mock_process(event):
        print("mock_process called")
        return "Mocked response"

