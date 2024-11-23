from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler
from plugins.genai_interactions.text.openai_chatgpt.openai_chatgpt import (
    OpenaiChatgptPlugin,
)


# Fixtures for mock config and global manager
@pytest.fixture
def mock_openai_chatgpt_config():
    return {
        "PLUGIN_NAME": "openai_chatgpt",
        "OPENAI_CHATGPT_API_KEY": "fake_key",
        "OPENAI_CHATGPT_MODEL_NAME": "gpt-3.5-turbo",
        "OPENAI_CHATGPT_VISION_MODEL_NAME": "gpt-vision",
        "OPENAI_CHATGPT_INPUT_TOKEN_PRICE": 0.01,
        "OPENAI_CHATGPT_OUTPUT_TOKEN_PRICE": 0.01,
        "OPENAI_CHATGPT_IS_ASSISTANT": False,
        "OPENAI_CHATGPT_ASSISTANT_ID": "",  # Change None to empty string
    }

@pytest.fixture
def mock_async_openai():
    with patch('plugins.genai_interactions.text.openai_chatgpt.openai_chatgpt.AsyncOpenAI') as mock_async_openai_class:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_async_openai_class.return_value = mock_client
        yield mock_client.chat.completions.create


@pytest.fixture(autouse=True)
def mock_openai_acreate():
    with patch('openai.ChatCompletion.acreate', new_callable=AsyncMock) as mock_acreate:
        yield mock_acreate

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_openai_chatgpt_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.TEXT = {
        "OPENAI_CHATGPT": mock_openai_chatgpt_config
    }
    return mock_global_manager

@pytest.fixture
def openai_chatgpt_plugin(extended_mock_global_manager):
    plugin = OpenaiChatgptPlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

# Test Initialization
@pytest.mark.asyncio
async def test_initialize(openai_chatgpt_plugin):
    openai_chatgpt_plugin.input_handler = None  # Reset
    openai_chatgpt_plugin.initialize()

    assert openai_chatgpt_plugin.openai_api_key == "fake_key"
    assert openai_chatgpt_plugin.model_name == "gpt-3.5-turbo"
    assert isinstance(openai_chatgpt_plugin.input_handler, ChatInputHandler)

# Test Handle Action
@pytest.mark.asyncio
async def test_handle_action(openai_chatgpt_plugin):
    action_input = ActionInput(
        action_name="generate_text",
        parameters={
            "input": "test input",
            "main_prompt": "test prompt",
            "context": "test context", 
            "conversation_data": "test conversation",
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'append_messages', new_callable=MagicMock) as mock_append_messages, \
         patch.object(openai_chatgpt_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:

        fake_session = MagicMock()
        fake_session.messages = []
        fake_session.session_id = "test_session"
        mock_get_or_create_session.return_value = fake_session

        def append_message(messages, message, session_id):
            messages.append(message)
            
        mock_append_messages.side_effect = append_message
        
        genai_cost_base = GenAICostBase(
            total_tk=100,
            prompt_tk=50,
            completion_tk=50,
            input_token_price=0.01,
            output_token_price=0.02
        )
        mock_generate_completion.return_value = ("Generated response", genai_cost_base)

        result = await openai_chatgpt_plugin.handle_action(action_input, event)

        assert result == "Generated response"
        assert len(fake_session.messages) == 2
        mock_save_session.assert_called_once()

# Test Error Handling in handle_request
@pytest.mark.asyncio
async def test_handle_request_with_error(openai_chatgpt_plugin):
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.input_handler, 'handle_event_data', new_callable=AsyncMock) as mock_handle_event_data, \
         patch.object(openai_chatgpt_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message:

        mock_handle_event_data.side_effect = Exception("Test Error")

        response = await openai_chatgpt_plugin.handle_request(event)

        assert response is None
        mock_send_message.assert_called()

# Test Generate Completion
@pytest.mark.asyncio
async def test_generate_completion(openai_chatgpt_plugin):
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:
        mock_generate_completion.return_value = ("Generated response", GenAICostBase(total_tk=100, prompt_tk=50, completion_tk=50))

        response, genai_cost_base = await openai_chatgpt_plugin.generate_completion(messages, event)

        assert response == "Generated response"
        assert genai_cost_base.total_tk == 100
        assert genai_cost_base.prompt_tk == 50
        assert genai_cost_base.completion_tk == 50

@pytest.mark.asyncio
async def test_handle_action_with_missing_parameters(openai_chatgpt_plugin):
    action_input = ActionInput(
        action_name="generate_text",
        parameters={
            "main_prompt": "test prompt"
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:

        fake_session = MagicMock()
        fake_session.messages = []
        mock_get_or_create_session.return_value = fake_session

        genai_cost_base = GenAICostBase(
            total_tk=100,
            prompt_tk=50,
            completion_tk=50,
            input_token_price=0.01,
            output_token_price=0.02
        )
        mock_generate_completion.return_value = ("Generated response", genai_cost_base)

        result = await openai_chatgpt_plugin.handle_action(action_input, event)

        assert result == "Generated response"
        assert len(fake_session.messages) == 2
        mock_save_session.assert_called_once()

@pytest.mark.asyncio
async def test_handle_action_without_main_prompt(openai_chatgpt_plugin):
    action_input = ActionInput(
        action_name="generate_text",
        parameters={
            "input": "test input",
            "context": "test context", 
            "conversation_data": "test conversation"
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'append_messages', new_callable=MagicMock) as mock_append_messages, \
         patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:

        messages_list = []
        fake_session = MagicMock()
        fake_session.session_id = "test_session" 
        messages_property = PropertyMock(return_value=messages_list)
        type(fake_session).messages = messages_property
        mock_get_or_create_session.return_value = fake_session

        def append_message(messages_list, message, session_id):
            messages_list.append(message)
            
        mock_append_messages.side_effect = append_message

        genai_cost_base = GenAICostBase(
            total_tk=100,
            prompt_tk=50,
            completion_tk=50,
            input_token_price=0.01,
            output_token_price=0.02
        )
        mock_generate_completion.return_value = ("Generated response", genai_cost_base)

        result = await openai_chatgpt_plugin.handle_action(action_input, event)

        assert result == "Generated response"
        assert len(messages_list) == 2
        mock_save_session.assert_called_once()

@pytest.mark.asyncio
async def test_handle_action_with_missing_parameters(openai_chatgpt_plugin):
    action_input = ActionInput(
        action_name="generate_text",
        parameters={
            "main_prompt": "test prompt"
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'save_session', new_callable=AsyncMock) as mock_save_session, \
         patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'append_messages', new_callable=MagicMock) as mock_append_messages, \
         patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:

        messages_list = []
        fake_session = MagicMock()
        fake_session.session_id = "test_session"
        messages_property = PropertyMock(return_value=messages_list)
        type(fake_session).messages = messages_property
        mock_get_or_create_session.return_value = fake_session

        def append_message(messages_list, message, session_id):
            messages_list.append(message)
            
        mock_append_messages.side_effect = append_message

        genai_cost_base = GenAICostBase(
            total_tk=100,
            prompt_tk=50,
            completion_tk=50,
            input_token_price=0.01,
            output_token_price=0.02
        )
        mock_generate_completion.return_value = ("Generated response", genai_cost_base)

        result = await openai_chatgpt_plugin.handle_action(action_input, event)

        assert result == "Generated response"
        assert len(messages_list) == 2
        mock_save_session.assert_called_once()

@pytest.mark.asyncio
async def test_handle_action_error(openai_chatgpt_plugin):
    action_input = ActionInput(
        action_name="generate_text",
        parameters={"input": "test input"}
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
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session, \
         patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion, \
         patch.object(openai_chatgpt_plugin.logger, 'error') as mock_logger_error:

        mock_get_or_create_session.side_effect = Exception("Test exception")

        with pytest.raises(Exception, match="Test exception"):
            await openai_chatgpt_plugin.handle_action(action_input, event)

        mock_logger_error.assert_called_once_with("Error in handle_action: Test exception")

async def trigger_genai(self, event: IncomingNotificationDataBase):
    AUTOMATED_RESPONSE_TRIGGER = "Automated response"
    event_copy = event

    if event.thread_id == '':
        response_id = event_copy.timestamp
    else:
        response_id = event_copy.thread_id

    event_copy.user_id = "AUTOMATED_RESPONSE"
    event_copy.user_name = AUTOMATED_RESPONSE_TRIGGER
    event_copy.user_email = AUTOMATED_RESPONSE_TRIGGER
    event_copy.event_label = "thread_message"

    # Await the coroutine
    user_message = await self.user_interaction_dispatcher.format_trigger_genai_message(event=event, message=event_copy.text)
    event_copy.text = user_message
    event_copy.is_mention = True
    event_copy.thread_id = response_id

    self.logger.debug(f"Triggered automated response on behalf of the user: {event_copy.text}")
    await self.user_interaction_dispatcher.send_message(event=event_copy, message="Processing incoming data, please wait...", message_type=MessageType.COMMENT)

    word_count = len(event_copy.text.split())

    if word_count > 300:
        await self.user_interaction_dispatcher.upload_file(event=event_copy, file_content=event_copy.text, filename="Bot reply.txt", title="Automated User Input", is_internal=True)
    else:
        await self.user_interaction_dispatcher.send_message(event=event_copy, message=f"AutomatedUserInput: {event_copy.text}", message_type=MessageType.TEXT, is_internal=True)

    await self.global_manager.user_interactions_behavior_dispatcher.process_incoming_notification_data(event_copy)


@pytest.mark.asyncio
async def test_generate_completion_with_image(openai_chatgpt_plugin):
    messages = [{"role": "user", "content": "Describe this image"}]
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
        origin_plugin_name="openai_chatgpt",
        images=["fake_image_data"]
    )

    with patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:
        mock_generate_completion.return_value = ("Image description response", GenAICostBase(total_tk=100, prompt_tk=50, completion_tk=50))

        response, genai_cost_base = await openai_chatgpt_plugin.generate_completion(messages, event)

        assert response == "Image description response"
        mock_generate_completion.assert_called_once()

# Test for camel_case function
def test_camel_case(openai_chatgpt_plugin):
    # Typical case
    assert openai_chatgpt_plugin.camel_case("hello_world") == "HelloWorld"

    # Single word, should capitalize
    assert openai_chatgpt_plugin.camel_case("hello") == "Hello"

    # Edge case: empty string
    assert openai_chatgpt_plugin.camel_case("") == ""

    # Multiple underscores
    assert openai_chatgpt_plugin.camel_case("hello_world_again") == "HelloWorldAgain"


# Test for normalize_keys function
def test_normalize_keys(openai_chatgpt_plugin):
    # Typical case: simple dict
    snake_case_dict = {"hello_world": "value", "my_key": 123}
    expected_camel_case_dict = {"HelloWorld": "value", "MyKey": 123}
    assert openai_chatgpt_plugin.normalize_keys(snake_case_dict) == expected_camel_case_dict

    # Nested dicts
    nested_snake_case_dict = {"outer_key": {"inner_key": "value"}, "another_key": 456}
    expected_nested_camel_case_dict = {"OuterKey": {"InnerKey": "value"}, "AnotherKey": 456}
    assert openai_chatgpt_plugin.normalize_keys(nested_snake_case_dict) == expected_nested_camel_case_dict

    # List of dicts
    list_of_dicts = [{"my_key": "value1"}, {"another_key": "value2"}]
    expected_list_of_camel_case_dicts = [{"MyKey": "value1"}, {"AnotherKey": "value2"}]
    assert openai_chatgpt_plugin.normalize_keys(list_of_dicts) == expected_list_of_camel_case_dicts

    # Empty dictionary
    assert openai_chatgpt_plugin.normalize_keys({}) == {}

    # Empty list
    assert openai_chatgpt_plugin.normalize_keys([]) == []

    # List of primitive types
    assert openai_chatgpt_plugin.normalize_keys([1, "string", 3.14]) == [1, "string", 3.14]

# Test for basic completion
# Test for basic completion
@pytest.mark.asyncio
async def test_generate_completion_basic(openai_chatgpt_plugin):
    messages = [{"role": "user", "content": "test message"}]
    event = IncomingNotificationDataBase(
        timestamp="2023-01-01T00:00:00Z",
        event_label="test_event",
        channel_id="channel_id",
        thread_id="thread_id",
        response_id="response_id",
        is_mention=True,
        text="user text",
        origin_plugin_name="openai_chatgpt"
    )

    with patch.object(openai_chatgpt_plugin, 'generate_completion', new_callable=AsyncMock) as mock_generate_completion:
        mock_generate_completion.return_value = ("Generated response", GenAICostBase(total_tk=100, prompt_tk=50, completion_tk=50))

        response, genai_cost_base = await openai_chatgpt_plugin.generate_completion(messages, event)

        assert response == "Generated response"
        assert genai_cost_base.total_tk == 100
        assert genai_cost_base.prompt_tk == 50
        assert genai_cost_base.completion_tk == 50

@pytest.mark.asyncio
async def test_generate_completion_with_json_markers(openai_chatgpt_plugin, mock_async_openai):
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
        origin_plugin_name="openai_chatgpt"
    )

    # Créer une réponse de complétion fictive
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="[BEGINIMDETECT]Hello[ENDIMDETECT]"))]
    mock_completion.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)

    # Configurer le mock pour retourner la réponse fictive
    mock_async_openai.return_value = mock_completion

    response, genai_cost_base = await openai_chatgpt_plugin.generate_completion(messages, event)

    # Assertions
    assert '[BEGINIMDETECT]' in response
    assert '[ENDIMDETECT]' in response
    assert genai_cost_base.total_tk == 100
    assert genai_cost_base.prompt_tk == 50
    assert genai_cost_base.completion_tk == 50

    # Vérifiez que 'acreate' a été appelé correctement
    mock_async_openai.assert_awaited_once_with(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.1,
        max_tokens=4096
    )

@pytest.mark.asyncio
async def test_generate_completion_with_vision_model(openai_chatgpt_plugin, mock_async_openai):
    messages = [{"role": "user", "content": "Describe this image"}]
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
        origin_plugin_name="openai_chatgpt",
        images=["fake_image_data"]
    )

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="Image description"))]
    mock_completion.usage = MagicMock(total_tokens=50, prompt_tokens=30, completion_tokens=20)

    # Configurer le mock pour retourner la réponse fictive
    mock_async_openai.return_value = mock_completion

    response, genai_cost_base = await openai_chatgpt_plugin.generate_completion(messages, event)

    # Assertions
    assert response == "Image description"
    assert genai_cost_base.total_tk == 50
    assert genai_cost_base.prompt_tk == 30
    assert genai_cost_base.completion_tk == 20

    # Vérifiez que 'acreate' a été appelé correctement avec le modèle de vision
    mock_async_openai.assert_awaited_once_with(
        model="gpt-vision",
        messages=messages,
        temperature=0.1,
        max_tokens=4096
    )


@pytest.mark.asyncio
async def test_generate_completion_with_images_but_no_vision_model(openai_chatgpt_plugin):
    messages = [{"role": "user", "content": "Describe this image"}]
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
        origin_plugin_name="openai_chatgpt",
        images=["fake_image_data"]
    )

    # Simulate missing vision model configuration
    openai_chatgpt_plugin.openai_chatgpt_config.OPENAI_CHATGPT_VISION_MODEL_NAME = None

    with patch.object(openai_chatgpt_plugin.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message:
        result = await openai_chatgpt_plugin.generate_completion(messages, event)

        mock_send_message.assert_called_once_with(
            event=event,
            message="Image received without genai interpreter in config",
            message_type=MessageType.COMMENT
        )
        assert result is None
