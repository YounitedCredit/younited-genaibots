import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.text.azure_chatgpt.azure_chatgpt import (
    AzureChatgptPlugin,
    MessageType,
)
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_chatgpt",  # Plugin name
        "AZURE_CHATGPT_INPUT_TOKEN_PRICE": 0.01,  # Input token price
        "AZURE_CHATGPT_OUTPUT_TOKEN_PRICE": 0.01,  # Output token price
        "AZURE_CHATGPT_OPENAI_KEY": "fake_key",  # OpenAI key
        "AZURE_CHATGPT_OPENAI_ENDPOINT": "https://fake_endpoint",  # OpenAI endpoint
        "AZURE_CHATGPT_OPENAI_API_VERSION": "v1",  # OpenAI API version
        "AZURE_CHATGPT_MODEL_NAME": "gpt-35-turbo",  # GPT model name
        "AZURE_CHATGPT_VISION_MODEL_NAME": "gpt-35-vision",  # Vision model name
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    # Update the mock global manager configuration to match the real one
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
             patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content, \
             patch.object(azure_chatgpt_plugin.session_manager, 'save_session', new_callable=AsyncMock) as mock_save_session, \
             patch.object(azure_chatgpt_plugin.session_manager, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session:

            # Create a fake session with a messages attribute
            fake_session = MagicMock()
            fake_session.messages = []
            mock_get_or_create_session.return_value = fake_session

            # Simulate empty blob
            mock_read_data_content.return_value = ""

            action_input = ActionInput(
                action_name='generate_text',
                parameters={
                    'input': 'test input',
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

            # Execute the action
            result = await azure_chatgpt_plugin.handle_action(action_input, event)
            assert result == "Generated response"

            # Assertions to check if the required calls were made
            mock_create.assert_called_once_with(
                model="gpt-35-turbo",
                temperature=0.1,
                top_p=0.1,
                messages=[
                    {"role": "user", "content": "Here is additional context: test context"},
                    {"role": "user", "content": "Conversation data: test conversation"},
                    {"role": "user", "content": "test input"}
                ],
                max_tokens=4096,
                seed=69
            )

            # Assert that calculate_and_update_costs was called
            mock_calculate_and_update_costs.assert_called_once()

            # Assert that the session was saved
            mock_save_session.assert_called_once()

            # Assert that write_data_content was called
            mock_write_data_content.assert_called_once()

class FakeSession:
    def __init__(self, channel_id: str, thread_id: str):
        self.channel_id = channel_id
        self.thread_id = thread_id
        self.events = []

@pytest.mark.asyncio
async def test_handle_action_with_existing_blob(azure_chatgpt_plugin):
    with patch.object(azure_chatgpt_plugin.gpt_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create, \
         patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(azure_chatgpt_plugin.input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_and_update_costs, \
         patch.object(azure_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'write_data_content', new_callable=AsyncMock) as mock_write_data_content, \
         patch.object(azure_chatgpt_plugin.session_manager, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(azure_chatgpt_plugin.session_manager, 'save_session', new_callable=AsyncMock) as mock_save_session:

        # Create a fake session object with real attributes
        fake_session = FakeSession(channel_id="channel_id", thread_id="thread_id")
        # Pre-populate the session with existing messages
        fake_session.events = [{"role": "assistant", "content": "previous message"}]
        fake_session.messages = [{"role": "assistant", "content": "previous message"}]
        mock_get_or_create_session.return_value = fake_session

        # Define the side effect for save_session to call write_data_content
        async def save_session_side_effect(session):
            # Ensure the session is updated with new events
            session.events.append({
                'role': 'assistant',
                'content': 'Generated response'
            })
            session.messages.append({
                'role': 'assistant',
                'content': 'Generated response'
            })
            blob_name = f"{session.channel_id}-{session.thread_id or session.timestamp}.txt"
            content = json.dumps(session.events)
            await azure_chatgpt_plugin.backend_internal_data_processing_dispatcher.write_data_content(
                azure_chatgpt_plugin.backend_internal_data_processing_dispatcher.sessions,
                blob_name,
                content
            )

        mock_save_session.side_effect = save_session_side_effect

        # Simulate existing blob content
        existing_messages = [{"role": "assistant", "content": "previous message"}]
        mock_read_data_content.return_value = json.dumps(existing_messages)

        # Define the action input and event
        action_input = ActionInput(
            action_name='generate_text',
            parameters={
                'input': 'test input',
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
            origin_plugin_name='test_plugin'
        )

        # Mock the correct behavior of the response object
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="Generated response"))]

        # Execute the action
        result = await azure_chatgpt_plugin.handle_action(action_input, event)

        # Assert the result matches the expected response
        assert result == "Generated response"

        # Assertions to check if the required calls were made
        mock_create.assert_called_once_with(
            model="gpt-35-turbo",
            temperature=0.1,
            top_p=0.1,
            messages=[
                {"role": "system", "content": json.dumps(existing_messages)},
                {"role": "user", "content": "Here is additional context: test context"},
                {"role": "user", "content": "Conversation data: test conversation"},
                {"role": "user", "content": "test input"}
            ],
            max_tokens=4096,
            seed=69
        )

        # Assert that calculate_and_update_costs was called
        mock_calculate_and_update_costs.assert_called_once()

        # Assert that the session was saved
        mock_save_session.assert_called_once()

        # Assert that write_data_content was called
        mock_write_data_content.assert_called_once()

        # Verify the content written to the blob
        write_call_args = mock_write_data_content.call_args[0]
        assert write_call_args[0] == azure_chatgpt_plugin.backend_internal_data_processing_dispatcher.sessions
        assert write_call_args[1] == 'channel_id-thread_id.txt'

        # Parse the JSON content passed to write_data_content
        written_content = json.loads(write_call_args[2])
        assert len(written_content) == 2  # Ensure 2 events exist
        # Verify the existing assistant message
        assert written_content[0]['role'] == 'assistant'
        assert written_content[0]['content'] == "previous message"
        # Verify the assistant's response
        assert written_content[1]['role'] == 'assistant'
        assert written_content[1]['content'] == "Generated response"


def test_validate_request(azure_chatgpt_plugin):
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
        origin_plugin_name='test_plugin'
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
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin_plugin_name='test_plugin'
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

        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin_plugin_name='test_plugin'
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
        event_label="event_label",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
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

        # Fix the expected value to match the casing used in the event
        assert event.user_id == "AUTOMATED_RESPONSE"

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
