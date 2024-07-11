from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.vector_search.openai_file_search.openai_file_search import (
    OpenaiFileSearchPlugin,
)
import numpy as np
import pandas as pd

@pytest.fixture
def openai_file_search_plugin(mock_global_manager):
    mock_config = {
        "PLUGIN_NAME": "openai_file_search",
        "OPENAI_SEARCH_OPENAI_KEY": "fake_key",
        "OPENAI_SEARCH_OPENAI_ENDPOINT": "https://fake_endpoint",
        "OPENAI_SEARCH_OPENAI_API_VERSION": "v1",
        "OPENAI_SEARCH_MODEL_HOST": "openai",
        "OPENAI_SEARCH_MODEL_NAME": "gpt-35-turbo",
        "OPENAI_SEARCH_INPUT_TOKEN_PRICE": 0.01,
        "OPENAI_SEARCH_OUTPUT_TOKEN_PRICE": 0.01,
        "OPENAI_SEARCH_CONTEXT_EXTRACTION": True,
        "OPENAI_SEARCH_CONTEXT_EXTRACTION_BEFORE_RATIO": 0.1,
        "OPENAI_SEARCH_CONTEXT_EXTRACTION_AFTER_RATIO": 0.1,
        "OPENAI_SEARCH_TEXT_WEIGHT": 0.7,
        "OPENAI_SEARCH_TITLE_WEIGHT": 0.3,
        "OPENAI_SEARCH_USE_TITLE_IN_SEARCH": True,
        "OPENAI_SEARCH_RESULT_COUNT": 5,
    }

    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH = {"OPENAI_FILE_SEARCH": mock_config}

    plugin = OpenaiFileSearchPlugin(global_manager=mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(openai_file_search_plugin):
    assert openai_file_search_plugin.plugin_name == "openai_file_search"
    assert openai_file_search_plugin.openai_key == "fake_key"
    assert openai_file_search_plugin.openai_endpoint == "https://fake_endpoint"
    assert openai_file_search_plugin.openai_api_version == "v1"
    assert openai_file_search_plugin.model_name == "gpt-35-turbo"

@pytest.mark.asyncio
async def test_handle_action(openai_file_search_plugin):
    action_input = ActionInput(action_name="search", parameters={"query": "test query", "index_name": "test_index"})
    
    # Créer un mock pour l'événement
    mock_event = MagicMock(spec=IncomingNotificationDataBase)
    
    with patch.object(openai_file_search_plugin, 'call_search', new_callable=AsyncMock) as mock_call_search:
        mock_call_search.return_value = "search result"
        result = await openai_file_search_plugin.handle_action(action_input, mock_event)
        assert result == "search result"
        mock_call_search.assert_called_once_with(query="test query", index_name="test_index", result_count=openai_file_search_plugin.result_count)

@pytest.mark.asyncio
async def test_call_search_with_results(openai_file_search_plugin):
    query = "test query"
    index_name = "test_index"
    expected_result = [("doc1", "passage_id", 1.0, "This is a passage", "title", "file_path")]
    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.return_value = "passage_index,text,embedding\n0,This is a passage,[0.1,0.2,0.3]"
        with patch.object(openai_file_search_plugin, 'search_reviews', new_callable=AsyncMock) as mock_search_reviews:
            mock_search_reviews.return_value = [("doc1", "passage_id", 1.0, "This is a passage", "title", "file_path")]
            result = await openai_file_search_plugin.call_search(query=query, index_name=index_name)
            assert result == [("doc1", "passage_id", 1.0, "This is a passage", "title", "file_path")]
        assert result == expected_result

@pytest.mark.asyncio
async def test_call_search_without_results(openai_file_search_plugin):
    query = "test query"
    index_name = "test_index"
    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.return_value = "passage_index,text,embedding\n"
        with patch.object(openai_file_search_plugin, 'search_reviews', new_callable=AsyncMock) as mock_search_reviews:
            mock_search_reviews.return_value = []
            result = await openai_file_search_plugin.call_search(query=query, index_name=index_name)
            assert result == []

@pytest.mark.asyncio
async def test_handle_request(openai_file_search_plugin):
    event = IncomingNotificationDataBase(
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
    with patch.object(openai_file_search_plugin, 'handle_action', new_callable=AsyncMock) as mock_handle_action:
        mock_handle_action.return_value = "action result"
        await openai_file_search_plugin.handle_request(event)

        assert mock_handle_action.call_count == 1
        call_args = mock_handle_action.call_args[0][0]
        assert call_args.action_name == "search"
        assert call_args.parameters == {"query": event.text}

@pytest.mark.asyncio
async def test_get_embedding(openai_file_search_plugin):
    with patch.object(openai_file_search_plugin.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.data = [AsyncMock(embedding=[0.1, 0.2, 0.3])]
        result = await openai_file_search_plugin.get_embedding("test text", "test_model")
        assert result == [0.1, 0.2, 0.3]
        mock_create.assert_called_once_with(input=["test text"], model="test_model")

def test_cosine_similarity(openai_file_search_plugin):
    a = np.array([1, 0, 1])
    b = np.array([0, 1, 1])
    result = openai_file_search_plugin.cosine_similarity(a, b)
    assert np.isclose(result, 0.5)

@pytest.mark.asyncio
async def test_extract_context(openai_file_search_plugin):
    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.return_value = "This is a long text for context extraction test."
        result = await openai_file_search_plugin.extract_context("index_name", "doc_id", 10, 20)
        assert "long text for context" in result  # Changé cette assertion
        assert len(result) <= len("This is a long text for context extraction test.")  # Ajouté cette assertion
        mock_read_data_content.assert_called_once_with(data_container="index_name", data_file="doc_id")

@pytest.mark.asyncio
async def test_call_search_error_handling(openai_file_search_plugin):
    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.side_effect = Exception("Test error")
        with pytest.raises(Exception):
            await openai_file_search_plugin.call_search("query", "index_name")

def test_validate_request(openai_file_search_plugin):
    event = IncomingNotificationDataBase(
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
    assert openai_file_search_plugin.validate_request(event) == True