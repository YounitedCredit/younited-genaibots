import json
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)

from plugins.genai_interactions.text.azure_chatgpt.azure_chatgpt import (
    AzureChatgptPlugin,
    MessageType
)

from plugins.genai_interactions.text.chat_input_handler import (
    ChatInputHandler
)

from core.genai_interactions.genai_cost_base import GenAICostBase

@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_chatgpt",
        "AZURE_CHATGPT_INPUT_TOKEN_PRICE": 0.01,
        "AZURE_CHATGPT_OUTPUT_TOKEN_PRICE": 0.01,
        "AZURE_OPENAI_KEY": "fake_key",
        "AZURE_OPENAI_ENDPOINT": "https://fake_endpoint",
        "OPENAI_API_VERSION": "v1",
        "AZURE_CHATGPT_MODEL_NAME": "gpt-35-turbo",
        "AZURE_CHATGPT_VISION_MODEL_NAME": "gpt-35-vision",
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "AZURE_CHATGPT": mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_chatgpt_plugin(extended_mock_global_manager):
    plugin = AzureChatgptPlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

@pytest.mark.asyncio
async def test_initialize(azure_chatgpt_plugin):
    # Reset the plugin to its pre-initialized state
    azure_chatgpt_plugin.gpt_client = None
    azure_chatgpt_plugin.input_handler = None

    # Call initialize
    azure_chatgpt_plugin.initialize()

    # Assert that the client and input handler are properly set up
    assert azure_chatgpt_plugin.gpt_client is not None
    assert isinstance(azure_chatgpt_plugin.input_handler, ChatInputHandler)
    assert azure_chatgpt_plugin.user_interaction_dispatcher is not None
    assert azure_chatgpt_plugin.genai_interactions_text_dispatcher is not None
    assert azure_chatgpt_plugin.backend_internal_data_processing_dispatcher is not None


@pytest.mark.asyncio
async def test_handle_action_with_empty_blob(azure_chatgpt_plugin):
    with patch.object(azure_chatgpt_plugin.gpt_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(azure_chatgpt_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

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

            result = await azure_chatgpt_plugin.handle_action(action_input, event)
            assert result == "Generated response"
            mock_create.assert_called_once_with(
                model="gpt-35-turbo",
                temperature=0.1,
                top_p=0.1,
                messages=[
                    {"role": "system", "content": ""},
                    {"role": "user", "content": "Here is aditionnal context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request: test conversation"},
                    {"role": "user", "content": "test input"}
                ],
                max_tokens=4096,
                seed=69
            )
            mock_write_data_content.assert_called_once()
            mock_calculate_and_update_costs.assert_called_once()

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(azure_chatgpt_plugin):
    with patch.object(azure_chatgpt_plugin.gpt_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

        with patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
             patch.object(azure_chatgpt_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
             patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content:

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

            result = await azure_chatgpt_plugin.handle_action(action_input, event)
            assert result == "Generated response"
            mock_create.assert_called_once_with(
                model="gpt-35-turbo",
                temperature=0.1,
                top_p=0.1,
                messages=[
                    {"role": "system", "content": json.dumps(existing_messages)},
                    {"role": "user", "content": "Here is aditionnal context relevant to the following request: test context"},
                    {"role": "user", "content": "Here is the conversation that led to the following request: test conversation"},
                    {"role": "user", "content": "test input"}
                ],
                max_tokens=4096,
                seed=69
            )
            mock_write_data_content.assert_called_once()
            mock_calculate_and_update_costs.assert_called_once()

            # Verify that the new message is appended to the existing ones
            expected_messages = existing_messages + [{"role": "assistant", "content": "Generated response"}]
            mock_write_data_content.assert_called_with(
                azure_chatgpt_plugin.backend_internal_data_processing_dispatcher.sessions,
                f"{event.channel_id}-{event.thread_id or event.timestamp}.txt",
                json.dumps(expected_messages)
            )

def test_validate_request(azure_chatgpt_plugin):
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
    assert azure_chatgpt_plugin.validate_request(event) == True

@pytest.mark.asyncio
async def test_handle_request(azure_chatgpt_plugin):
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
    with patch.object(azure_chatgpt_plugin.input_handler, 'handle_event_data', new_callable=AsyncMock) as mock_handle_event_data:
        mock_handle_event_data.return_value = "Mocked response"
        response = await azure_chatgpt_plugin.handle_request(event)
        assert response == "Mocked response"
        mock_handle_event_data.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_generate_completion(azure_chatgpt_plugin):
    messages = [{"role": "user", "content": "Hello"}]
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
    with patch.object(azure_chatgpt_plugin.gpt_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices[0].message.content = "Generated response"
        mock_create.return_value.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
        
        response, genai_cost_base = await azure_chatgpt_plugin.generate_completion(messages, event)
        
        assert response == "Generated response"
        assert genai_cost_base.total_tk == 100
        assert genai_cost_base.prompt_tk == 50
        assert genai_cost_base.completion_tk == 50
        assert genai_cost_base.input_token_price == azure_chatgpt_plugin.input_token_price
        assert genai_cost_base.output_token_price == azure_chatgpt_plugin.output_token_price

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

    # Mock synchrone qui retourne directement une chaîne
    mock_format_trigger_genai_message = MagicMock(return_value="<@BOT123> user text")

    with patch.object(azure_chatgpt_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message, \
         patch.object(azure_chatgpt_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_incoming_notification_data', new_callable=AsyncMock) as mock_process, \
         patch.object(azure_chatgpt_plugin.user_interaction_dispatcher, 'format_trigger_genai_message', mock_format_trigger_genai_message):

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
        mock_format_trigger_genai_message.assert_called_once_with(event=event, message="user text")
        
        # Vérifiez que les attributs de l'événement ont été correctement modifiés
        assert event.user_id == "Automated response"
        assert event.user_name == "Automated response"
        assert event.user_email == "Automated response"
        assert event.event_label == "thread_message"
        assert event.text == "<@BOT123> user text"
        assert event.is_mention == True
        assert event.thread_id == "thread_id"

@pytest.mark.asyncio
async def test_generate_completion_assistant(azure_chatgpt_plugin, mock_incoming_notification_data_base):
    # Configuration du plugin
    azure_chatgpt_plugin.azure_chatgpt_config.AZURE_CHATGPT_IS_ASSISTANT = True
    azure_chatgpt_plugin.azure_chatgpt_config.AZURE_CHATGPT_ASSISTANT_ID = "test_assistant_id"
    azure_chatgpt_plugin.azure_chatgpt_config.AZURE_CHATGPT_VISION_MODEL_NAME = "gpt-4-vision-preview"

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather like?"},
        {"role": "assistant", "content": "I'm sorry, I don't have real-time weather information."},
        {"role": "user", "content": "Can you analyze this image?"}
    ]

    event_data = mock_incoming_notification_data_base
    event_data.images = ["base64_encoded_image_data"]

    # Créer des mocks pour tous les appels asynchrones
    async def mock_create_thread(*args, **kwargs):
        return AsyncMock(id="test_thread_id")

    async def mock_create_message(*args, **kwargs):
        return AsyncMock()

    async def mock_create_run(*args, **kwargs):
        return AsyncMock(id="test_run_id", status="completed")

    async def mock_retrieve_run(*args, **kwargs):
        return AsyncMock(status="completed")

    async def mock_list_messages(*args, **kwargs):
        return MagicMock(data=[MagicMock(content=[MagicMock(text=MagicMock(value="This is the assistant's response."))])])

    async def mock_create_completion(*args, **kwargs):
        return AsyncMock(choices=[MagicMock(message=MagicMock(content="This is an image of a sunny day."))])

    with patch.object(azure_chatgpt_plugin.gpt_client.beta.threads, 'create', side_effect=mock_create_thread), \
         patch.object(azure_chatgpt_plugin.gpt_client.beta.threads.messages, 'create', side_effect=mock_create_message), \
         patch.object(azure_chatgpt_plugin.gpt_client.beta.threads.runs, 'create', side_effect=mock_create_run), \
         patch.object(azure_chatgpt_plugin.gpt_client.beta.threads.runs, 'retrieve', side_effect=mock_retrieve_run), \
         patch.object(azure_chatgpt_plugin.gpt_client.beta.threads.messages, 'list', side_effect=mock_list_messages), \
         patch.object(azure_chatgpt_plugin.gpt_client.chat.completions, 'create', side_effect=mock_create_completion):

        response, genai_cost_base = await azure_chatgpt_plugin.generate_completion_assistant(messages, event_data)

        # Ajoutez ici vos assertions pour vérifier le résultat
        assert response == "This is the assistant's response."
        assert isinstance(genai_cost_base, GenAICostBase)

@pytest.mark.asyncio
async def test_generate_completion_assistant_error(azure_chatgpt_plugin, mock_incoming_notification_data_base):
    azure_chatgpt_plugin.azure_chatgpt_config.AZURE_CHATGPT_IS_ASSISTANT = True
    azure_chatgpt_plugin.azure_chatgpt_config.AZURE_CHATGPT_ASSISTANT_ID = "test_assistant_id"

    messages = [{"role": "user", "content": "Hello"}]
    event_data = mock_incoming_notification_data_base

    with patch.object(azure_chatgpt_plugin.gpt_client.beta.threads, 'create', side_effect=Exception("Test error")), \
         patch.object(azure_chatgpt_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message:

        with pytest.raises(Exception):
            await azure_chatgpt_plugin.generate_completion_assistant(messages, event_data)

        mock_send_message.assert_called_once_with(
            event=event_data,
            message="An unexpected error occurred during assistant completion",
            message_type=MessageType.COMMENT,  # Changé de ERROR à COMMENT
            is_internal=True
        )