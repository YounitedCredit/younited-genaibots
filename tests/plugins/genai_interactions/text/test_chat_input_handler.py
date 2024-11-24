import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler


@pytest.fixture
def mock_chat_plugin():
    """Mock for the GenAIInteractionsTextPluginBase."""
    return MagicMock(spec=GenAIInteractionsTextPluginBase)

@pytest.fixture
def chat_input_handler(mock_global_manager, mock_chat_plugin):
    """Fixture to initialize ChatInputHandler with mocked dependencies."""
    handler = ChatInputHandler(global_manager=mock_global_manager, chat_plugin=mock_chat_plugin)
    handler.initialize()
    return handler

@pytest.fixture
def incoming_notification():
    return IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="1633090572.000200",  # Unix timestamp example
        event_label="message",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin_plugin_name="plugin_name"
    )

@pytest.mark.asyncio
async def test_handle_event_data_thread_message(chat_input_handler, incoming_notification):
    incoming_notification.event_label = 'thread_message'
    with patch.object(chat_input_handler, 'handle_thread_message_event', new_callable=AsyncMock) as mock_handle_thread_message_event:
        mock_handle_thread_message_event.return_value = "Handled thread message event"
        result = await chat_input_handler.handle_event_data(incoming_notification)
        assert result == "Handled thread message event"
        mock_handle_thread_message_event.assert_called_once_with(incoming_notification)

@pytest.mark.asyncio
async def test_handle_message_event(mock_global_manager, mock_config_manager):
    event_data = IncomingNotificationDataBase(
        timestamp="1633090572.000200", event_label="message",
        channel_id="C12345", thread_id="T67890", response_id="R11111",
        is_mention=True, text="Hello", origin_plugin_name="test_plugin",
        user_id="U12345", user_name="test_user"
    )

    mock_session = MagicMock()
    mock_session.messages = []

    mock_prompt_manager = AsyncMock()
    mock_prompt_manager.initialize = AsyncMock()
    mock_prompt_manager.core_prompt = "Core Prompt"
    mock_prompt_manager.main_prompt = "Main Prompt"
    mock_global_manager.prompt_manager = mock_prompt_manager

    mock_global_manager.session_manager_dispatcher = AsyncMock()
    mock_global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(return_value=mock_session)
    mock_global_manager.session_manager_dispatcher.save_session = AsyncMock()
    mock_global_manager.session_manager_dispatcher.append_messages = MagicMock()

    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks = 'mock_feedbacks_container'
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value='{"feedback": "positive"}')

    mock_global_manager.bot_config = MagicMock(
        FEEDBACK_GENERAL_BEHAVIOR='feedback_general_behavior',
        CORE_PROMPT='core_prompt_name',
        MAIN_PROMPT='main_prompt_name',
        LLM_CONVERSION_FORMAT='json'
    )

    chat_handler = ChatInputHandler(global_manager=mock_global_manager, chat_plugin=AsyncMock())
    chat_handler.generate_response = AsyncMock(return_value={"response": "Mocked response"})
    chat_handler.initialize()

    response = await chat_handler.handle_message_event(event_data)
    assert response == {"response": "Mocked response"}

@pytest.mark.asyncio
async def test_generate_response(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler.global_manager.user_interactions_behavior_dispatcher, 'begin_genai_completion', new_callable=AsyncMock) as mock_begin_genai_completion, \
         patch.object(chat_input_handler, 'call_completion', new_callable=AsyncMock) as mock_call_completion, \
         patch.object(chat_input_handler.global_manager.user_interactions_behavior_dispatcher, 'end_genai_completion', new_callable=AsyncMock) as mock_end_genai_completion:

        mock_call_completion.return_value = {"response": "generated completion"}
        session = MagicMock()
        session.messages = [{"role": "system", "content": "init_prompt"}]

        result = await chat_input_handler.generate_response(incoming_notification, session)
        assert result == {"response": "generated completion"}
        mock_begin_genai_completion.assert_called_once()
        mock_call_completion.assert_called_once()
        mock_end_genai_completion.assert_called_once()

@pytest.mark.asyncio
async def test_handle_event_data_exception(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler, 'handle_message_event', side_effect=Exception("Test exception")):
        with pytest.raises(Exception, match="Test exception"):
            await chat_input_handler.handle_event_data(incoming_notification)

@pytest.mark.asyncio
async def test_handle_message_event_with_images(chat_input_handler, incoming_notification):
    incoming_notification.images = ["base64_image_data"]

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = {"response": "response with image"}

        # Act
        result = await chat_input_handler.handle_message_event(incoming_notification)

        # Assert
        assert result == {"response": "response with image"}
        mock_generate_response.assert_called_once()

@pytest.mark.asyncio
async def test_handle_message_event_with_files(chat_input_handler):
    event_data = MagicMock(
        files_content=["file1", "file2"],
        images=["img1", "img2"],
        timestamp="1633090572.000200",
        channel_id="C12345", thread_id="T67890",
        user_id="U12345", user_name="test_user",
        user_email="test@example.com", is_mention=True,
        text="Hello"
    )

    messages = []
    mock_session = MagicMock()
    mock_session.messages = messages

    mock_prompt_manager = AsyncMock()
    mock_prompt_manager.initialize = AsyncMock()
    mock_prompt_manager.core_prompt = "Core Prompt"
    mock_prompt_manager.main_prompt = "Main Prompt"
    chat_input_handler.global_manager.prompt_manager = mock_prompt_manager

    # Correction ici: on ne fait qu'un seul append
    def append_mock(msg_list, msg, _):
        msg_list.append(msg)
        return msg_list

    chat_input_handler.session_manager_dispatcher = MagicMock()
    chat_input_handler.session_manager_dispatcher.append_messages.side_effect = append_mock
    chat_input_handler.global_manager.session_manager_dispatcher = AsyncMock()
    chat_input_handler.global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(return_value=mock_session)
    chat_input_handler.global_manager.session_manager_dispatcher.save_session = AsyncMock()
    chat_input_handler.generate_response = AsyncMock(return_value="response with files")
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="test content")

    await chat_input_handler.handle_message_event(event_data)
    assert len(messages) == 2

@pytest.mark.asyncio
async def test_call_completion_success(chat_input_handler):
    # Arrange
    mock_messages = [{"role": "user", "content": "test message"}]
    event_data = IncomingNotificationDataBase(
        timestamp="1633090572.000200",
        event_label="message",
        channel_id="C12345",
        thread_id="T67890",
        response_id="R11111",
        is_mention=True,
        text="test message",
        origin_plugin_name="test_plugin",
        user_id="U12345",
        user_name="test_user"
    )

    chat_input_handler.chat_plugin = AsyncMock()

    # Mock a dictionary with a 'response' key as expected by the code
    mock_response = {
        "response": [
            {
                "Action": {
                    "ActionName": "test_action",
                    "Parameters": {"param1": "value1"}
                }
            }
        ]
    }

    # Return the mock response as a dictionary and MagicMock for cost
    chat_input_handler.chat_plugin.generate_completion.return_value = (json.dumps(mock_response), MagicMock())
    chat_input_handler.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    chat_input_handler.conversion_format = "json"

    session = MagicMock()

    # Act
    result = await chat_input_handler.call_completion(
        event_data.channel_id,
        event_data.thread_id,
        mock_messages,
        event_data,
        session
    )

    # Assert
    assert result == mock_response
    chat_input_handler.chat_plugin.generate_completion.assert_called_once()


@pytest.mark.asyncio
async def test_call_completion_failure(chat_input_handler, incoming_notification):
    mock_messages = [{"role": "user", "content": "test message"}]
    session = MagicMock()

    # Simulate an exception during completion
    chat_input_handler.chat_plugin.generate_completion = AsyncMock(side_effect=Exception("Mocked exception"))

    with patch.object(chat_input_handler, 'handle_completion_errors', new_callable=AsyncMock) as mock_handle_completion_errors:
        await chat_input_handler.call_completion(incoming_notification.channel_id, incoming_notification.thread_id, mock_messages, incoming_notification, session)
        mock_handle_completion_errors.assert_called_once()

@pytest.mark.asyncio
async def test_handle_event_data_invalid_label(chat_input_handler, incoming_notification):
    # Test handling event data with an invalid event label
    incoming_notification.event_label = "unknown_label"
    with pytest.raises(ValueError, match="Unknown event label: unknown_label"):
        await chat_input_handler.handle_event_data(incoming_notification)

@pytest.mark.asyncio
async def test_handle_message_event_with_large_file_content(chat_input_handler):
    event_data = MagicMock(
        files_content=["content"] * 21,
        timestamp="1633090572.000200",
        channel_id="C12345", thread_id="T67890",
        user_id="U12345", user_name="test_user",
        user_email="test@example.com", is_mention=True,
        text="Hello", images=[]
    )

    messages = []
    mock_session = MagicMock()
    mock_session.messages = messages

    mock_prompt_manager = AsyncMock()
    mock_prompt_manager.initialize = AsyncMock()
    mock_prompt_manager.core_prompt = "Core Prompt"
    mock_prompt_manager.main_prompt = "Main Prompt"
    chat_input_handler.global_manager.prompt_manager = mock_prompt_manager

    # Même correction
    def append_mock(msg_list, msg, _):
        msg_list.append(msg)
        return msg_list

    chat_input_handler.session_manager_dispatcher = MagicMock()
    chat_input_handler.session_manager_dispatcher.append_messages.side_effect = append_mock
    chat_input_handler.global_manager.session_manager_dispatcher = AsyncMock()
    chat_input_handler.global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(return_value=mock_session)
    chat_input_handler.global_manager.session_manager_dispatcher.save_session = AsyncMock()
    chat_input_handler.generate_response = AsyncMock(return_value="response")
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="test")

    await chat_input_handler.handle_message_event(event_data)
    assert len(messages) == 2

@pytest.mark.asyncio
async def test_generate_response_with_error(chat_input_handler, incoming_notification):
    mock_messages = [{"role": "system", "content": "test system prompt"}]

    # Patch directement la méthode de l'instance
    with patch.object(chat_input_handler, 'call_completion', new_callable=AsyncMock) as mock_call_completion:
        mock_call_completion.side_effect = Exception("Test exception")

        session = MagicMock()
        session.messages = mock_messages

        with pytest.raises(Exception, match="Test exception"):
            await chat_input_handler.generate_response(incoming_notification, session)

        mock_call_completion.assert_called_once()

@pytest.mark.asyncio
async def test_yaml_to_json_success(chat_input_handler, incoming_notification):
    yaml_string = """
    response:
      - Action:
          Parameters:
            value:
              name: Test
              description: A test action
    """
    result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)

    # Assurez-vous que le résultat est un dictionnaire correctement analysé
    assert result is not None, "The YAML string was not converted to a dictionary"
    assert isinstance(result, dict), "The result is not a dictionary"
    assert result['response'][0]['Action']['Parameters']['value']['name'] == 'Test'


@pytest.mark.asyncio
async def test_yaml_to_json_error(chat_input_handler, incoming_notification):
    # Test yaml_to_json with an invalid YAML string
    yaml_string = "invalid: yaml: string"

    with patch.object(chat_input_handler, 'logger') as mock_logger:
        result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)
        assert result is None
        mock_logger.error.assert_called()

@pytest.mark.asyncio
async def test_handle_message_event_exception(chat_input_handler, incoming_notification):
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=Exception("Read content failed"))
    chat_input_handler.global_manager.session_manager_dispatcher.get_or_create_session = AsyncMock(side_effect=Exception("Read content failed"))

    with pytest.raises(Exception, match="Read content failed"):
        await chat_input_handler.handle_message_event(incoming_notification)

@pytest.mark.asyncio
async def test_handle_thread_message_event_no_messages(chat_input_handler, incoming_notification):
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="[]")

    with patch.object(chat_input_handler, 'process_conversation_history', new_callable=AsyncMock) as mock_process_conversation_history, \
         patch.object(chat_input_handler.global_manager.prompt_manager, 'initialize', new_callable=AsyncMock) as mock_initialize_prompt, \
         patch.object(chat_input_handler.global_manager.session_manager_dispatcher, 'get_or_create_session', new_callable=AsyncMock) as mock_get_or_create_session:

        mock_session = MagicMock()
        mock_session.messages = []
        mock_get_or_create_session.return_value = mock_session

        result = await chat_input_handler.handle_thread_message_event(incoming_notification)
        assert result is None
        mock_initialize_prompt.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_and_update_costs(chat_input_handler, incoming_notification):
    cost_params = MagicMock(total_tk=1000, prompt_tk=500, completion_tk=500, input_token_price=0.02, output_token_price=0.03)
    chat_input_handler.backend_internal_data_processing_dispatcher.update_pricing = AsyncMock()
    mock_session = MagicMock()

    total_cost, input_cost, output_cost = await chat_input_handler.calculate_and_update_costs(
        cost_params, "costs_container", "blob_name", incoming_notification, mock_session
    )

    assert total_cost == 0.025
    assert input_cost == 0.01
    assert output_cost == 0.015

def test_get_last_user_message_timestamp(chat_input_handler):
    messages = [
        {"role": "assistant", "content": "Some assistant message"},
        {"role": "user", "content": [{"type": "text", "text": "Timestamp: 2023-09-14 10:00:00, user message"}], "timestamp": "2023-09-14 10:00:00"},
        {"role": "user", "content": [{"type": "text", "text": "Timestamp: 2023-09-15 11:00:00, another user message"}], "timestamp": "2023-09-15 11:00:00"},
    ]

    timestamp = chat_input_handler.get_last_user_message_timestamp(messages)
    assert timestamp == "2023-09-15 11:00:00"

def test_convert_events_to_messages(chat_input_handler):
    messages = []
    msg_list = []
    events = [
        MagicMock(
            user_name="User1", user_id="123", text="Hello",
            images=[], files_content=[], timestamp="1633090572.000200",
            user_email="user1@test.com", is_mention=True
        ),
        MagicMock(
            user_name="User2", user_id="456", text="Hi",
            images=[], files_content=[], timestamp="1633090573.000200",
            user_email="user2@test.com", is_mention=True
        )
    ]

    def append_mock(msg_list, msg, _):
        msg_list.append(msg)
        messages.append(msg)
        return msg_list

    chat_input_handler.session_manager_dispatcher = MagicMock()
    chat_input_handler.session_manager_dispatcher.append_messages.side_effect = append_mock
    result = chat_input_handler.convert_events_to_messages(events, 'test_session')

    assert len(messages) == 2
    assert all(msg["role"] == "user" for msg in messages)
    assert "Hello" in messages[0]["content"][0]["text"]
    assert "Hi" in messages[1]["content"][0]["text"]

def test_construct_message(chat_input_handler):
    # Simulated event data with text, images, and files
    event_data = MagicMock(
        user_name="User1",
        user_id="123",
        user_email="user1@example.com",
        is_mention=True,
        text="Hello",
        images=["image_data_base64"],
        files_content=["file content"]
    )

    message = chat_input_handler.construct_message(event_data)

    # Check that the message contains the expected text, image, and file content
    assert message["role"] == "user"
    assert "Hello" in message["content"][0]["text"]
    assert message["content"][1]["type"] == "text"
    assert message["content"][2]["type"] == "image_url"
    assert message["content"][2]["image_url"]["url"] == "data:image/jpeg;base64,image_data_base64"

def test_adjust_yaml_structure(chat_input_handler):
    # Simulated YAML content
    yaml_string = """
    response:
      - Action:
          Parameters:
            value: |
              Line 1
              Line 2
    """

    adjusted_yaml = chat_input_handler.adjust_yaml_structure(yaml_string).strip()  # Use strip to remove leading/trailing spaces

    # Check that the YAML content is properly adjusted
    assert "Line 1" in adjusted_yaml
    assert "Line 2" in adjusted_yaml
    assert adjusted_yaml.startswith("response:")  # This should now pass with the leading newline removed
    assert "- Action:" in adjusted_yaml



@pytest.mark.asyncio
async def test_handle_completion_errors(chat_input_handler, incoming_notification):
    # Simulated exception
    exception = Exception("Test error with message: 'Test error'")

    with patch.object(chat_input_handler.user_interaction_dispatcher, 'send_message', new_callable=AsyncMock) as mock_send_message:
        await chat_input_handler.handle_completion_errors(incoming_notification, exception)

        mock_send_message.assert_called()
        assert "Test error" in mock_send_message.call_args[1]['message']

@pytest.mark.asyncio
async def test_process_conversation_history_no_history(chat_input_handler):
    # Arrange
    event_data = MagicMock()
    session = MagicMock()
    chat_input_handler.user_interaction_dispatcher.fetch_conversation_history = AsyncMock(return_value=[])
    chat_input_handler.logger = MagicMock()

    # Act
    await chat_input_handler.process_conversation_history(event_data, session)

    # Assert
    chat_input_handler.user_interaction_dispatcher.fetch_conversation_history.assert_called_once_with(event=event_data)
    chat_input_handler.logger.warning.assert_called_once()
    assert "No conversation history found" in chat_input_handler.logger.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_session_cost_accumulation(chat_input_handler, incoming_notification):
    initial_total_cost = 0.0
    session = MagicMock()
    session.total_cost = {'total_tokens': 0, 'total_cost': initial_total_cost}

    # Define side effect for accumulate_cost
    def accumulate_cost_side_effect(cost_dict):
        session.total_cost['total_tokens'] += cost_dict['total_tokens']
        session.total_cost['total_cost'] += cost_dict['total_cost']

    session.accumulate_cost = accumulate_cost_side_effect

    chat_input_handler.backend_internal_data_processing_dispatcher.update_pricing = AsyncMock()

    await chat_input_handler.calculate_and_update_costs(
        cost_params=GenAICostBase(
            total_tk=1000, prompt_tk=500, completion_tk=500,
            input_token_price=0.02, output_token_price=0.03
        ),
        costs_blob_container_name='costs_container',
        blob_name='blob_name',
        event=incoming_notification,
        session=session
    )

    assert session.total_cost['total_cost'] > initial_total_cost
    assert session.total_cost['total_tokens'] == 1000
    assert session.total_cost['total_cost'] == 0.025  # Calculated total cost
