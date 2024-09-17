import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.text.chat_input_handler import ChatInputHandler

@pytest.fixture
def mock_chat_plugin():
    return MagicMock(spec=GenAIInteractionsTextPluginBase)

@pytest.fixture
def chat_input_handler(mock_global_manager, mock_chat_plugin):
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
        timestamp="timestamp",
        converted_timestamp="2023-09-13 10:00:00",  
        event_label="message",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin",
        origin_plugin_name="plugin_name"
    )

@pytest.mark.asyncio
async def test_handle_event_data_message(chat_input_handler, incoming_notification):
    incoming_notification.event_label = 'message'
    with patch.object(chat_input_handler, 'handle_message_event', new_callable=AsyncMock) as mock_handle_message_event:
        mock_handle_message_event.return_value = "Handled message event"
        result = await chat_input_handler.handle_event_data(incoming_notification)
        assert result == "Handled message event"
        mock_handle_message_event.assert_called_once_with(incoming_notification)

@pytest.mark.asyncio
async def test_handle_event_data_thread_message(chat_input_handler, incoming_notification):
    incoming_notification.event_label = 'thread_message'
    with patch.object(chat_input_handler, 'handle_thread_message_event', new_callable=AsyncMock) as mock_handle_thread_message_event:
        mock_handle_thread_message_event.return_value = "Handled thread message event"
        result = await chat_input_handler.handle_event_data(incoming_notification)
        assert result == "Handled thread message event"
        mock_handle_thread_message_event.assert_called_once_with(incoming_notification)

@pytest.mark.asyncio
async def test_handle_message_event(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(chat_input_handler.global_manager.prompt_manager, 'initialize', new_callable=AsyncMock) as mock_initialize_prompt, \
         patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:

        mock_read_data_content.return_value = "general behavior content"
        mock_initialize_prompt.return_value = "prompt"
        mock_generate_response.return_value = "generated response"

        result = await chat_input_handler.handle_message_event(incoming_notification)
        assert result == "generated response"
        mock_read_data_content.assert_called_once()
        mock_initialize_prompt.assert_called_once()
        mock_generate_response.assert_called_once()

@pytest.mark.asyncio
async def test_handle_thread_message_event(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'store_unmentioned_messages', new_callable=AsyncMock) as mock_store_unmentioned_messages, \
         patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:

        mock_read_data_content.return_value = json.dumps([{"role": "assistant", "content": "previous message"}])
        mock_generate_response.return_value = "generated response"
        incoming_notification.is_mention = False

        result = await chat_input_handler.handle_thread_message_event(incoming_notification)
        assert result is None
        mock_read_data_content.assert_called_once()
        mock_store_unmentioned_messages.assert_called_once()

@pytest.mark.asyncio
async def test_generate_response(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler.global_manager.user_interactions_behavior_dispatcher, 'begin_genai_completion', new_callable=AsyncMock) as mock_begin_genai_completion, \
         patch.object(chat_input_handler, 'call_completion', new_callable=AsyncMock) as mock_call_completion, \
         patch.object(chat_input_handler.global_manager.user_interactions_behavior_dispatcher, 'end_genai_completion', new_callable=AsyncMock) as mock_end_genai_completion:

        mock_call_completion.return_value = "generated response"
        result = await chat_input_handler.generate_response(incoming_notification, [{"role": "system", "content": "init_prompt"}])
        assert result == "generated response"
        mock_begin_genai_completion.assert_called_once()
        mock_call_completion.assert_called_once()
        mock_end_genai_completion.assert_called_once()

@pytest.mark.asyncio
async def test_handle_event_data_exception(chat_input_handler, incoming_notification):
    with patch.object(chat_input_handler, 'handle_message_event', side_effect=Exception("Test exception")):
        with pytest.raises(Exception):
            await chat_input_handler.handle_event_data(incoming_notification)

@pytest.mark.asyncio
async def test_handle_message_event_with_images(chat_input_handler, incoming_notification):
    incoming_notification.images = ["base64_image_data"]

    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="mocked general behavior content")
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock(return_value="mocked track")
    chat_input_handler.global_manager.prompt_manager.core_prompt = "mocked core prompt"
    chat_input_handler.global_manager.prompt_manager.main_prompt = "mocked main prompt"

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "response with image"

        result = await chat_input_handler.handle_message_event(incoming_notification)
        assert result == "response with image"

        mock_generate_response.assert_called_once()
        call_args = mock_generate_response.call_args[0]
        assert call_args[0] == incoming_notification
        messages = call_args[1]
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert "mocked core prompt" in messages[0]['content']
        assert "mocked main prompt" in messages[0]['content']
        assert messages[1]['role'] == 'user'
        assert isinstance(messages[1]['content'], list)
        assert len(messages[1]['content']) == 2
        assert messages[1]['content'][0]['type'] == 'text'
        assert messages[1]['content'][1]['type'] == 'image_url'
        assert messages[1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')

@pytest.mark.asyncio
async def test_handle_message_event_with_files(chat_input_handler, incoming_notification):
    incoming_notification.files_content = ["file content 1", "file content 2"]
    incoming_notification.images = ["base64_image_data_1", "base64_image_data_2"]
    incoming_notification.converted_timestamp = "2024-01-01T00:00:00Z"  

    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="mocked general behavior content")
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock(return_value="mocked track")
    chat_input_handler.global_manager.prompt_manager.core_prompt = "mocked core prompt"
    chat_input_handler.global_manager.prompt_manager.main_prompt = "mocked main prompt"

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "response with files"

        result = await chat_input_handler.handle_message_event(incoming_notification)
        assert result == "response with files"

        mock_generate_response.assert_called_once()
        call_args = mock_generate_response.call_args[0]
        assert call_args[0] == incoming_notification
        messages = call_args[1]
        assert messages[0]['role'] == 'system'
        expected_system_content = (
            f"{chat_input_handler.global_manager.prompt_manager.core_prompt}\n"
            f"{chat_input_handler.global_manager.prompt_manager.main_prompt}\n"
            f"Also take into account these previous general behavior feedbacks constructed with user feedback from previous plugins, "
            f"take them as the prompt not another feedback to add: mocked general behavior content"
        )
        assert messages[0]['content'] == expected_system_content

        assert messages[1]['role'] == 'user'
        user_content = messages[1]['content']
        assert user_content[0]['type'] == 'text'
        expected_text = (
            f"Timestamp: {incoming_notification.converted_timestamp}, [username]: {incoming_notification.user_name}, "
            f"[user id]: {incoming_notification.user_id}, [user email]: {incoming_notification.user_email}, "
            f"[Directly mentioning you]: {incoming_notification.is_mention}, [message]: {incoming_notification.text}"
        )
        assert user_content[0]['text'] == expected_text
        assert user_content[1]['type'] == 'text'
        assert user_content[1]['text'] == "file content 1"
        assert user_content[2]['type'] == 'text'
        assert user_content[2]['text'] == "file content 2"
        assert user_content[3]['type'] == 'image_url'
        assert user_content[3]['image_url']['url'] == "data:image/jpeg;base64,base64_image_data_1"
        assert user_content[4]['type'] == 'image_url'
        assert user_content[4]['image_url']['url'] == "data:image/jpeg;base64,base64_image_data_2"
        assert len(user_content) == 5

@pytest.mark.asyncio
async def test_call_completion_success(chat_input_handler, incoming_notification):
    mock_messages = [{"role": "user", "content": "test message"}]

    # Mock the generate_completion method to return a valid JSON response string
    valid_json_response = '{"response": "generated completion"}'
    chat_input_handler.chat_plugin.generate_completion = AsyncMock(return_value=(valid_json_response, MagicMock()))

    # Mock the update_pricing method
    chat_input_handler.backend_internal_data_processing_dispatcher.update_pricing = AsyncMock(return_value=MagicMock())

    # Mock conversion_format to JSON
    chat_input_handler.conversion_format = "json"

    # Mock the session write method
    chat_input_handler.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    # Test JSON format
    result = await chat_input_handler.call_completion(incoming_notification.channel_id, incoming_notification.thread_id, mock_messages, incoming_notification)

    # Vérifiez si le résultat est bien ce qui est attendu et analysé en JSON
    assert result is not None
    assert result["response"] == "generated completion"



@pytest.mark.asyncio
async def test_call_completion_failure(chat_input_handler, incoming_notification):
    # Test the call_completion method when an exception occurs
    mock_messages = [{"role": "user", "content": "test message"}]
    
    # Mock the generate_completion method to raise an exception
    chat_input_handler.chat_plugin.generate_completion = AsyncMock(side_effect=Exception("Mocked exception"))

    with patch.object(chat_input_handler, 'handle_completion_errors', new_callable=AsyncMock) as mock_handle_completion_errors:
        await chat_input_handler.call_completion(incoming_notification.channel_id, incoming_notification.thread_id, mock_messages, incoming_notification)
        mock_handle_completion_errors.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_genai_with_thread(chat_input_handler, incoming_notification):
    # Test triggering GenAI with a thread of messages
    mock_messages = [{"role": "user", "content": "test message"}]

    with patch.object(chat_input_handler, 'call_completion', new_callable=AsyncMock) as mock_call_completion:
        mock_call_completion.return_value = "generated thread response"
        result = await chat_input_handler.trigger_genai_with_thread(incoming_notification, mock_messages)
        assert result == "generated thread response"
        mock_call_completion.assert_called_once_with(incoming_notification.channel_id, incoming_notification.thread_id, mock_messages, incoming_notification)


@pytest.mark.asyncio
async def test_handle_event_data_invalid_label(chat_input_handler, incoming_notification):
    # Test handling event data with an invalid event label
    incoming_notification.event_label = "unknown_label"
    with pytest.raises(ValueError, match="Unknown event label: unknown_label"):
        await chat_input_handler.handle_event_data(incoming_notification)


@pytest.mark.asyncio
async def test_handle_message_event_with_large_file_content(chat_input_handler, incoming_notification):
    # Test handling a message event with a large number of file contents
    incoming_notification.files_content = ["file content"] * 21  # More than 20 files
    incoming_notification.images = []

    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="mocked general behavior content")
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock()

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        await chat_input_handler.handle_message_event(incoming_notification)
        messages = mock_generate_response.call_args[0][1]
        assert len(messages[1]['content']) == 23  # 21 file contents + constructed message + reminder message


@pytest.mark.asyncio
async def test_generate_response_with_error(chat_input_handler, incoming_notification):
    # Test generate_response method when an error occurs in call_completion
    mock_messages = [{"role": "system", "content": "test system prompt"}]

    # Mock the call_completion method to raise an exception
    chat_input_handler.call_completion = AsyncMock(side_effect=Exception("Test exception"))

    with pytest.raises(Exception, match="Test exception"):
        await chat_input_handler.generate_response(incoming_notification, mock_messages)


@pytest.mark.asyncio
async def test_handle_thread_message_event_with_no_messages(chat_input_handler, incoming_notification):
    incoming_notification.is_mention = False
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="[]")
    chat_input_handler.global_manager.bot_config.RECORD_NONPROCESSED_MESSAGES = False

    with patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'store_unmentioned_messages', new_callable=AsyncMock) as mock_store_unmentioned_messages:
        result = await chat_input_handler.handle_thread_message_event(incoming_notification)
        assert result is None


@pytest.mark.asyncio
async def test_yaml_to_json_success(chat_input_handler, incoming_notification):
    yaml_string = """
    response:
      - Action:
          Parameters:
            value: |
              name: Test
              description: A test action
    """
    result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)

    # Ensure the result is a properly parsed dictionary
    assert isinstance(result, dict)
    assert result['response'][0]['Action']['Parameters']['value']['name'] == 'Test'


@pytest.mark.asyncio
async def test_yaml_to_json_error(chat_input_handler, incoming_notification):
    # Test yaml_to_json with an invalid YAML string
    yaml_string = "invalid: yaml: string"

    with patch.object(chat_input_handler, 'logger') as mock_logger:
        result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)
        assert result is None
        mock_logger.error.assert_called()