import json
from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.vector_search import (
    VectorSearch,
)


@pytest.mark.asyncio
async def test_vector_search_initialization(mock_global_manager):
    # Setup
    vector_search_action = VectorSearch(global_manager=mock_global_manager)

    # Assert that the object is initialized correctly
    assert vector_search_action.global_manager == mock_global_manager
    assert vector_search_action.user_interactions_dispatcher == mock_global_manager.user_interactions_dispatcher
    assert vector_search_action.genai_interactions_text_dispatcher == mock_global_manager.genai_interactions_text_dispatcher
    assert vector_search_action.vector_search_dispatcher == mock_global_manager.genai_vectorsearch_dispatcher
    assert vector_search_action.backend_internal_data_processing_dispatcher == mock_global_manager.backend_internal_data_processing_dispatcher


@pytest.mark.asyncio
async def test_vector_search_execute_with_results(mock_global_manager):
    # Setup
    vector_search_action = VectorSearch(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='vector_search', parameters={'query': 'Test query', 'index_name': 'test_index', 'result_count': 5})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name="origin_plugin_name"
    )

    # Mock methods
    mock_results = [
        {'id': 'doc1', '@search.score': 0.95, 'content': 'Test text 1', 'title': 'Test title 1', 'file_path': 'path1'},
        {'id': 'doc2', '@search.score': 0.90, 'content': 'Test text 2', 'title': 'Test title 2', 'file_path': 'path2'}
    ]
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()
    mock_global_manager.genai_vectorsearch_dispatcher.handle_action = AsyncMock(return_value=json.dumps({"search_results": mock_results}))
    mock_global_manager.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    # Execute the action
    await vector_search_action.execute(action_input, event)

    # Assert that send_message was called correctly to indicate search start
    assert any(
        call.kwargs['message'] == "Looking at existing documentation..."
        and call.kwargs['message_type'] == MessageType.COMMENT
        for call in mock_global_manager.user_interactions_dispatcher.send_message.call_args_list
    )

    # Assert that trigger_genai was called with the correct message
    assert mock_global_manager.genai_interactions_text_dispatcher.trigger_genai.call_count == 1
    event_copy = mock_global_manager.genai_interactions_text_dispatcher.trigger_genai.call_args[1]['event']
    assert "Here's the result from the vector db search" in event_copy.text


@pytest.mark.asyncio
async def test_vector_search_execute_no_results(mock_global_manager):
    # Setup
    vector_search_action = VectorSearch(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='vector_search', parameters={'query': 'Test query', 'index_name': 'test_index', 'result_count': 5})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name="origin_plugin_name"
    )

    # Mock methods
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()
    mock_global_manager.genai_vectorsearch_dispatcher.handle_action = AsyncMock(return_value=[])
    mock_global_manager.genai_interactions_text_dispatcher.trigger_genai = AsyncMock()

    # Execute the action
    await vector_search_action.execute(action_input, event)

    # Assert that send_message was called correctly to indicate search start
    assert any(
        call.kwargs['message'] == "Looking at existing documentation..."
        and call.kwargs['message_type'] == MessageType.COMMENT
        for call in mock_global_manager.user_interactions_dispatcher.send_message.call_args_list
    )

    # Assert that send_message was called to indicate no results found
    assert any(
        call.kwargs['message'] == "Vector search failed, sorry about that :/ see logs for more details"
        and call.kwargs['message_type'] == MessageType.COMMENT
        for call in mock_global_manager.user_interactions_dispatcher.send_message.call_args_list
    )


@pytest.mark.asyncio
async def test_vector_search_execute_with_exception(mock_global_manager):
    # Setup
    vector_search_action = VectorSearch(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='vector_search', parameters={'query': 'Test query', 'index_name': 'test_index', 'result_count': 5})
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name="origin_plugin_name"
    )

    # Mock methods to raise an exception
    mock_global_manager.user_interactions_dispatcher.send_message = AsyncMock()
    mock_global_manager.genai_vectorsearch_dispatcher.handle_action = AsyncMock(side_effect=Exception("Test exception"))

    # Execute the action
    await vector_search_action.execute(action_input, event)

    # Assert that the exception was logged
    mock_global_manager.logger.exception.assert_called_with("An error occurred: Test exception")

    # Print the call arguments to inspect them
    print(mock_global_manager.user_interactions_dispatcher.send_message.call_args_list)

    # Assert that send_message was called with the correct failure message
    assert any(
        "Vector search failed, sorry about that :/ see logs for more details" in call.kwargs['message']
        and call.kwargs['message_type'] == MessageType.COMMENT
        for call in mock_global_manager.user_interactions_dispatcher.send_message.call_args_list
    )
