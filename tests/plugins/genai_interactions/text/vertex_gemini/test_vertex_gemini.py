import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.text.vertexai_gemini.vertexai_gemini import (
    VertexaiGeminiPlugin,
)


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "vertexai_gemini",
        "VERTEXAI_GEMINI_INPUT_TOKEN_PRICE": 0.07,
        "VERTEXAI_GEMINI_OUTPUT_TOKEN_PRICE": 0.21,
        "VERTEXAI_GEMINI_KEY": json.dumps({
            "type": "service_account",
            "project_id": "fake_project_id",
            "private_key_id": "fake_key_id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC...\n-----END PRIVATE KEY-----\n",
            "client_email": "fake_email",
            "client_id": "fake_client_id",
            "auth_uri": "https://fake_auth_uri",
            "token_uri": "https://fake_token_uri",
            "auth_provider_x509_cert_url": "https://fake_cert_url",
            "client_x509_cert_url": "https://fake_client_cert_url"
        }),
        "VERTEXAI_GEMINI_MODELNAME": "gemini_model",
        "VERTEXAI_GEMINI_PROJECTNAME": "fake_project",
        "VERTEXAI_GEMINI_LOCATION": "us-central1",
        "VERTEXAI_GEMINI_MAX_OUTPUT_TOKENS": 100,
        "VERTEXAI_GEMINI_TEMPERATURE": 0.7,
        "VERTEXAI_GEMINI_TOP_P": 0.9,
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "VERTEXAI_GEMINI": mock_config
    }
    return mock_global_manager

@pytest.fixture
def vertexai_gemini_plugin(extended_mock_global_manager):
    with patch('plugins.genai_interactions.text.vertexai_gemini.vertexai_gemini.GenerativeModel', new_callable=MagicMock) as mock_model:
        plugin = VertexaiGeminiPlugin(global_manager=extended_mock_global_manager)
        plugin.load_client = MagicMock()
        plugin.client = mock_model.return_value
        plugin.initialize()
    return plugin

def test_initialize(vertexai_gemini_plugin):
    assert vertexai_gemini_plugin.vertexai_gemini_input_token_price == 0.07
    assert vertexai_gemini_plugin.vertexai_gemini_output_token_price == 0.21
    assert vertexai_gemini_plugin.vertexai_gemini_projectname == "fake_project"
    assert vertexai_gemini_plugin.vertexai_gemini_location == "us-central1"
    assert vertexai_gemini_plugin.vertexai_gemini_modelname == "gemini_model"
    assert vertexai_gemini_plugin.plugin_name == "vertexai_gemini"

@pytest.mark.asyncio
async def test_handle_action_with_empty_blob(vertexai_gemini_plugin):
    with patch.object(vertexai_gemini_plugin.client, 'generate_content_async', new_callable=AsyncMock) as mock_generate:
        # Mock the response to return invalid JSON, simulating the invalid content case
        mock_generate.return_value = MagicMock(
            candidates=[MagicMock(content=MagicMock(parts=[MagicMock(text="Invalid JSON response")]))],
            usage_metadata=MagicMock(total_token_count=100, prompt_token_count=50, candidates_token_count=50)
        )

        with patch.object(vertexai_gemini_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(vertexai_gemini_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(vertexai_gemini_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

            # Simulate empty blob content
            mock_read_data_content.return_value = ""

            action_input = ActionInput(action_name='generate_text', parameters={
                'input': 'test input',
                'main_prompt': 'test prompt',
                'context': 'test context',
                'conversation_data': 'test conversation'
            })
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

            # Test that the result is None when invalid JSON is returned
            result = await vertexai_gemini_plugin.handle_action(action_input, event)
            assert result is None
            mock_generate.assert_called_once_with(json.dumps({
                "messages": [
                    {"role": "system", "content": ""},  # Empty content from the blob
                    {"role": "user", "content": "Here is additional context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request: test conversation"},
                    {"role": "user", "content": "test input"}
                ],
                "parameters": {
                    "temperature": vertexai_gemini_plugin.vertexai_gemini_temperature,
                    "top_p": vertexai_gemini_plugin.vertexai_gemini_top_p,
                    "max_tokens": vertexai_gemini_plugin.vertexai_gemini_max_output_tokens
                }
            }, ensure_ascii=False))

            # Ensure write_data_content was not called due to invalid JSON
            mock_write_data_content.assert_not_called()
            mock_calculate_and_update_costs.assert_not_called()

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(vertexai_gemini_plugin):
    with patch.object(vertexai_gemini_plugin.client, 'generate_content_async', new_callable=AsyncMock) as mock_generate:
        # Mock the response with invalid JSON
        mock_generate.return_value = MagicMock(
            candidates=[MagicMock(content=MagicMock(parts=[MagicMock(text="Invalid JSON response")]))],
            usage_metadata=MagicMock(total_token_count=100, prompt_token_count=50, candidates_token_count=50)
        )

        with patch.object(vertexai_gemini_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(vertexai_gemini_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(vertexai_gemini_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

            # Simulate existing blob content with valid JSON
            existing_messages = [{"role": "assistant", "content": "previous message"}]
            mock_read_data_content.return_value = json.dumps(existing_messages)

            action_input = ActionInput(action_name='generate_text', parameters={
                'input': 'test input',
                'main_prompt': 'test prompt',
                'context': 'test context',
                'conversation_data': 'test conversation'
            })
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

            # Test that the result is None when invalid JSON is returned
            result = await vertexai_gemini_plugin.handle_action(action_input, event)
            assert result is None  # Expecting None when invalid JSON is returned

            # Ensure the mock API was called with the expected arguments
            mock_generate.assert_called_once_with(json.dumps({
                "messages": [
                    {"role": "system", "content": json.dumps(existing_messages)},
                    {"role": "user", "content": "Here is additional context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request: test conversation"},
                    {"role": "user", "content": "test input"}
                ],
                "parameters": {
                    "temperature": vertexai_gemini_plugin.vertexai_gemini_temperature,
                    "top_p": vertexai_gemini_plugin.vertexai_gemini_top_p,
                    "max_tokens": vertexai_gemini_plugin.vertexai_gemini_max_output_tokens
                }
            }, ensure_ascii=False))

            # Since invalid JSON leads to None, write_data_content should not be called
            mock_write_data_content.assert_not_called()
            # calculate_and_update_costs should also not be called in this case
            mock_calculate_and_update_costs.assert_not_called()
