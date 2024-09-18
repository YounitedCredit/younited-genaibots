import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime, timezone

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
        timestamp="1633090572.000200",  # Unix timestamp example
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
    # Assurez-vous que le bot est configuré pour requérir une mention pour stocker les messages non mentionnés
    chat_input_handler.global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE = True
    
    # Spécifiez que l'utilisateur n'est pas mentionné (ce qui devrait déclencher 'store_unmentioned_messages')
    incoming_notification.is_mention = False
    
    # Mock les méthodes nécessaires
    with patch.object(chat_input_handler, 'process_relevant_events', return_value=[]), \
         patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content, \
         patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'store_unmentioned_messages', new_callable=AsyncMock) as mock_store_unmentioned_messages, \
         patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        
        # Simulez le contenu lu
        mock_read_data_content.return_value = json.dumps([{"role": "assistant", "content": "previous message"}])
        
        # Simulez une réponse générée
        mock_generate_response.return_value = "generated response"
        
        # Appelez la méthode
        result = await chat_input_handler.handle_thread_message_event(incoming_notification)
        
        # Assurez-vous que le résultat est None, car l'utilisateur n'est pas mentionné
        assert result is None

        # Vérifiez que 'read_data_content' a bien été appelée une fois
        mock_read_data_content.assert_called_once()

        # 'store_unmentioned_messages' devrait être appelée car l'utilisateur n'est pas mentionné
        mock_store_unmentioned_messages.assert_called_once_with(
            incoming_notification.channel_id, 
            incoming_notification.thread_id, 
            incoming_notification.text
        )
        
        # Vérifiez que 'generate_response' n'est pas appelée, car il ne devrait pas y avoir de réponse générée
        mock_generate_response.assert_not_called()

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
    incoming_notification.timestamp = "1633090572.000200"  # Un exemple valide de timestamp Unix

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
            f"Timestamp: {chat_input_handler.format_timestamp(incoming_notification.timestamp)}, [username]: {incoming_notification.user_name}, "
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
    # Mock the method that raises an exception
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(side_effect=Exception("Read content failed"))

    with pytest.raises(Exception, match="Read content failed"):
        await chat_input_handler.handle_message_event(incoming_notification)

@pytest.mark.asyncio
async def test_filter_messages_with_images(chat_input_handler):
    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": "Message content"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}
        ]}
    ]
    
    filtered_messages = await chat_input_handler.filter_messages(messages)
    
    # Assert that the image is removed and only the text remains
    assert len(filtered_messages[0]["content"]) == 1
    assert filtered_messages[0]["content"][0]["type"] == "text"
    assert filtered_messages[0]["content"][0]["text"] == "Message content"

@pytest.mark.asyncio
async def test_handle_thread_message_event_no_messages(chat_input_handler, incoming_notification):
    # Mock read_data_content to return an empty list of messages
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="[]")
    chat_input_handler.global_manager.bot_config.RECORD_NONPROCESSED_MESSAGES = False
    
    result = await chat_input_handler.handle_thread_message_event(incoming_notification)
    
    # Assert that the result is None when no messages are found
    assert result is None

@pytest.mark.asyncio
async def test_yaml_to_json_complex(chat_input_handler, incoming_notification):
    yaml_string = """
    response:
      - Action:
          Parameters:
            value:
              details: |
                Line 1
                Line 2
    """
    result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)

    assert result is not None, "The YAML string was not converted"
    assert isinstance(result, dict), "The result is not a dictionary"
    # Adjust the expected result to include the extra newline
    assert result['response'][0]['Action']['Parameters']['value']['details'] == 'Line 1\nLine 2\n'


@pytest.mark.asyncio
async def test_calculate_and_update_costs(chat_input_handler, incoming_notification):
    cost_params = MagicMock(total_tk=1000, prompt_tk=500, completion_tk=500, input_token_price=0.02, output_token_price=0.03)
    chat_input_handler.backend_internal_data_processing_dispatcher.update_pricing = AsyncMock()

    total_cost, input_cost, output_cost = await chat_input_handler.calculate_and_update_costs(
        cost_params, "costs_container", "blob_name", incoming_notification
    )
    
    assert total_cost == 0.025  # (500/1000) * 0.02 + (500/1000) * 0.03
    assert input_cost == 0.01  # (500/1000) * 0.02
    assert output_cost == 0.015  # (500/1000) * 0.03

def test_parse_timestamp_invalid(chat_input_handler):
    with pytest.raises(ValueError, match="time data 'invalid_timestamp' does not match format '%Y-%m-%d %H:%M:%S'"):
        chat_input_handler.parse_timestamp("invalid_timestamp")

def test_get_last_user_message_timestamp(chat_input_handler):
    # Messages with timestamps
    messages = [
        {"role": "assistant", "content": [{"type": "text", "text": "Some assistant message"}]},
        {"role": "user", "content": [{"type": "text", "text": "Timestamp: 2023-09-14 10:00:00, user message"}]},
        {"role": "user", "content": [{"type": "text", "text": "Timestamp: 2023-09-15 11:00:00, another user message"}]},
    ]

    # Expected to find the last user message's timestamp
    timestamp = chat_input_handler.get_last_user_message_timestamp(messages)

    assert timestamp == datetime.strptime("2023-09-15 11:00:00", "%Y-%m-%d %H:%M:%S")

def test_convert_events_to_messages(chat_input_handler):
    # Simulated events
    events = [
        MagicMock(user_name="User1", user_id="123", text="Hello", images=[], files_content=[]),
        MagicMock(user_name="User2", user_id="456", text="Hi", images=[], files_content=[])
    ]

    messages = chat_input_handler.convert_events_to_messages(events)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "Hello" in messages[0]["content"][0]["text"]
    assert messages[1]["role"] == "user"
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
