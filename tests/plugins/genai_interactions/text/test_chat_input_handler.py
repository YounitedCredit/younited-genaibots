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
        converted_timestamp="converted_timestamp",
        event_label="message",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin"
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

    # Mock the necessary methods
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="mocked general behavior content")
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock(return_value="mocked track")
    chat_input_handler.global_manager.prompt_manager.core_prompt = "mocked core prompt"
    chat_input_handler.global_manager.prompt_manager.main_prompt = "mocked main prompt"

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "response with image"

        result = await chat_input_handler.handle_message_event(incoming_notification)

        assert result == "response with image"

        # Check that generate_response was called with the correct arguments
        mock_generate_response.assert_called_once()
        call_args = mock_generate_response.call_args[0]
        assert call_args[0] == incoming_notification
        messages = call_args[1]

        # Check that the messages list is constructed correctly
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

    # Mock the necessary methods
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="mocked general behavior content")
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock(return_value="mocked track")
    chat_input_handler.global_manager.prompt_manager.core_prompt = "mocked core prompt"
    chat_input_handler.global_manager.prompt_manager.main_prompt = "mocked main prompt"

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "response with files"

        result = await chat_input_handler.handle_message_event(incoming_notification)

        assert result == "response with files"

        # Check that generate_response was called with the correct arguments
        mock_generate_response.assert_called_once()
        call_args = mock_generate_response.call_args[0]
        assert call_args[0] == incoming_notification
        messages = call_args[1]

        # Check that the messages list is constructed correctly
        assert len(messages) == 4  # system message, user message, 2 file content messages
        assert messages[0]['role'] == 'system'
        assert "mocked core prompt" in messages[0]['content']
        assert "mocked main prompt" in messages[0]['content']
        assert messages[1]['role'] == 'user'
        assert isinstance(messages[1]['content'], str)
        assert messages[2]['role'] == 'user'
        assert messages[2]['content'] == [{"type": "text", "text": "file content 1"}]
        assert messages[3]['role'] == 'user'
        assert messages[3]['content'] == [{"type": "text", "text": "file content 2"}]

@pytest.mark.asyncio
async def test_filter_messages(chat_input_handler):
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}, {"type": "image_url", "image_url": "some_url"}]},
        {"role": "assistant", "content": "Hi there!"}
    ]
    filtered = await chat_input_handler.filter_messages(messages)
    assert len(filtered) == 2
    assert len(filtered[0]['content']) == 1
    assert filtered[0]['content'][0]['type'] == "text"

@pytest.mark.asyncio
async def test_call_completion(chat_input_handler, incoming_notification, mock_chat_plugin):
    # Setup
    chat_input_handler.chat_plugin = mock_chat_plugin
    mock_chat_plugin.generate_completion.return_value = ("completion", MagicMock())

    # Mock necessary methods and attributes
    chat_input_handler.backend_internal_data_processing_dispatcher.costs = "costs_container"
    chat_input_handler.backend_internal_data_processing_dispatcher.sessions = "sessions_container"
    chat_input_handler.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()
    chat_input_handler.user_interaction_dispatcher.upload_file = AsyncMock()
    chat_input_handler.conversion_format = "yaml"  # or "json" depending on your configuration

    with patch.object(chat_input_handler, 'calculate_and_update_costs', new_callable=AsyncMock) as mock_calculate_costs, \
         patch.object(chat_input_handler, 'yaml_to_json', new_callable=AsyncMock) as mock_yaml_to_json, \
         patch.object(chat_input_handler, 'adjust_yaml_structure', return_value="adjusted yaml") as mock_adjust_yaml:

        mock_calculate_costs.return_value = (1.0, 0.5, 0.5)
        mock_yaml_to_json.return_value = {"response": "json data"}

        result = await chat_input_handler.call_completion("channel_id", "thread_id", [], incoming_notification)

        # Assertions
        assert result == {"response": "json data"}
        mock_chat_plugin.generate_completion.assert_called_once()
        mock_calculate_costs.assert_called_once()
        mock_adjust_yaml.assert_called_once_with("completion")
        mock_yaml_to_json.assert_called_once_with(event_data=incoming_notification, yaml_string="adjusted yaml")
        chat_input_handler.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once()
        chat_input_handler.user_interaction_dispatcher.upload_file.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_and_update_costs(chat_input_handler, incoming_notification):
    cost_params = MagicMock()
    cost_params.total_tk = 100
    cost_params.prompt_tk = 50
    cost_params.completion_tk = 50
    cost_params.input_token_price = 0.01
    cost_params.output_token_price = 0.02
    with patch.object(chat_input_handler.backend_internal_data_processing_dispatcher, 'update_pricing', new_callable=AsyncMock) as mock_update_pricing:
        mock_update_pricing.return_value = MagicMock()
        result = await chat_input_handler.calculate_and_update_costs(cost_params, "costs_container", "blob_name", incoming_notification)
        assert isinstance(result, tuple)
        assert len(result) == 3

@pytest.mark.asyncio
async def test_handle_message_event_with_many_files(chat_input_handler, incoming_notification):
    incoming_notification.files_content = [f"file content {i}" for i in range(21)]
    chat_input_handler.global_manager.prompt_manager.initialize = AsyncMock(return_value="mocked track")
    chat_input_handler.global_manager.prompt_manager.core_prompt = "core prompt"
    chat_input_handler.global_manager.prompt_manager.main_prompt = "main prompt"
    chat_input_handler.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="")

    with patch.object(chat_input_handler, 'generate_response', new_callable=AsyncMock) as mock_generate_response:
        mock_generate_response.return_value = "response with many files"

        result = await chat_input_handler.handle_message_event(incoming_notification)

        assert result == "response with many files"
        mock_generate_response.assert_called_once()
        call_args = mock_generate_response.call_args[0]
        messages = call_args[1]

        # Check if the reminder message is present in the last message
        reminder_message = "Remember to follow the core prompt rules: core prompt\nmain prompt"
        last_message = messages[-1]
        assert last_message['role'] == 'user'
        assert isinstance(last_message['content'], list)
        assert len(last_message['content']) == 1
        assert last_message['content'][0]['type'] == 'text'
        assert last_message['content'][0]['text'] == reminder_message

        # Optional: Check that there are 23 messages in total (1 system, 1 user, 21 file contents, 1 reminder)
        assert len(messages) == 24

@pytest.mark.asyncio
async def test_handle_completion_errors(chat_input_handler, incoming_notification):
    error = Exception("Test error 'message': \"Error details\", 'param': something")
    chat_input_handler.user_interaction_dispatcher.send_message = AsyncMock()
    chat_input_handler.logger.error = MagicMock()

    result = await chat_input_handler.handle_completion_errors(incoming_notification, error)

    assert result is None
    chat_input_handler.user_interaction_dispatcher.send_message.assert_called()
    chat_input_handler.logger.error.assert_called()
    assert chat_input_handler.user_interaction_dispatcher.send_message.call_count == 2
    assert "Error details" in chat_input_handler.user_interaction_dispatcher.send_message.call_args_list[1][1]['message']

def test_adjust_yaml_structure(chat_input_handler):
    yaml_content = """
response:
- Action:
    ActionName: TestAction
    Parameters:
      param1: value1
      param2: |
        multiline
        value
      param3: single line
    """
    adjusted = chat_input_handler.adjust_yaml_structure(yaml_content)
    expected = """response:
  - Action:
      ActionName: TestAction
      Parameters:
        param1: value1
        param2: |
        multiline
        value
        param3: single line"""

    # Normalize both strings by removing all leading/trailing whitespace from each line
    adjusted_normalized = "\n".join(line.strip() for line in adjusted.strip().split("\n"))
    expected_normalized = "\n".join(line.strip() for line in expected.strip().split("\n"))

    assert adjusted_normalized == expected_normalized, f"Adjusted:\n{adjusted}\n\nExpected:\n{expected}"

    # Additional structural checks
    assert "response:" in adjusted
    assert "- Action:" in adjusted
    assert "ActionName: TestAction" in adjusted
    assert "Parameters:" in adjusted
    assert "param1: value1" in adjusted
    assert "param2: |" in adjusted
    assert "multiline" in adjusted
    assert "value" in adjusted
    assert "param3: single line" in adjusted

@pytest.mark.asyncio
async def test_yaml_to_json(chat_input_handler, incoming_notification):
    yaml_string = """
response:
  - Action:
      ActionName: TestAction
      Parameters:
        value: |
          ```yaml
          key: value
          nested:
            subkey: subvalue
          ```
    """
    chat_input_handler.logger.error = MagicMock()
    chat_input_handler.user_interaction_dispatcher.send_message = AsyncMock()

    result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)

    assert isinstance(result, dict)
    assert 'response' in result
    assert isinstance(result['response'], list)
    assert len(result['response']) == 1
    assert 'Action' in result['response'][0]
    assert 'Parameters' in result['response'][0]['Action']
    assert 'value' in result['response'][0]['Action']['Parameters']

    # Check that the value is a string and contains the expected YAML content
    value = result['response'][0]['Action']['Parameters']['value']
    assert isinstance(value, str)
    assert 'key: value' in value
    assert 'nested:' in value
    assert 'subkey: subvalue' in value

    # Remove the Markdown code block delimiters and parse the YAML
    import yaml
    yaml_content = value.strip().replace('```yaml\n', '').replace('```', '')
    parsed_value = yaml.safe_load(yaml_content)
    assert parsed_value == {'key': 'value', 'nested': {'subkey': 'subvalue'}}

    print("Actual result:")
    print(result)

@pytest.mark.asyncio
async def test_yaml_to_json_error(chat_input_handler, incoming_notification):
    yaml_string = "invalid: yaml: content:"
    chat_input_handler.logger.error = MagicMock()
    chat_input_handler.user_interaction_dispatcher.send_message = AsyncMock()

    result = await chat_input_handler.yaml_to_json(incoming_notification, yaml_string)

    assert result is None
    chat_input_handler.logger.error.assert_called()
    chat_input_handler.user_interaction_dispatcher.send_message.assert_called()
