import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.vector_search.openai_file_search.openai_file_search import (
    OpenaiFileSearchPlugin,
)


@pytest.fixture
def openai_file_search_plugin(mock_global_manager):
    mock_config = {
        "PLUGIN_NAME": "openai_file_search",
        "OPENAI_FILE_SEARCH_OPENAI_KEY": "fake_key",
        "OPENAI_FILE_SEARCH_OPENAI_ENDPOINT": "https://fake_endpoint",
        "OPENAI_FILE_SEARCH_OPENAI_API_VERSION": "v1",
        "OPENAI_FILE_SEARCH_MODEL_HOST": "openai",
        "OPENAI_FILE_SEARCH_MODEL_NAME": "gpt-35-turbo",
        "OPENAI_FILE_SEARCH_RESULT_COUNT": 5,
        "OPENAI_FILE_SEARCH_INDEX_NAME": "test_index"
    }

    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH = {"OPENAI_FILE_SEARCH": mock_config}

    plugin = OpenaiFileSearchPlugin(global_manager=mock_global_manager)
    plugin.initialize()
    return plugin


def test_initialize(openai_file_search_plugin):
    assert openai_file_search_plugin.plugin_name == "openai_file_search"
    assert openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_KEY == "fake_key"
    assert openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_ENDPOINT == "https://fake_endpoint"
    assert openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_OPENAI_API_VERSION == "v1"
    assert openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_MODEL_NAME == "gpt-35-turbo"


@pytest.mark.asyncio
async def test_handle_action(openai_file_search_plugin):
    action_input = ActionInput(action_name="search", parameters={"query": "test query", "index_name": "test_index"})

    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    with patch.object(openai_file_search_plugin, 'call_search', new_callable=AsyncMock) as mock_call_search:
        mock_call_search.return_value = "search result"
        result = await openai_file_search_plugin.handle_action(action_input, mock_event)
        assert result == "search result"

        mock_call_search.assert_called_once_with(query="test query", index_name="test_index", result_count=openai_file_search_plugin.result_count, get_whole_doc=False)


@pytest.mark.asyncio
async def test_call_search_with_results(openai_file_search_plugin):
    query = "test query"
    index_name = "test_index"
    expected_result = [{"id": "doc1", "@search.score": 1.0}]

    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.return_value = json.dumps({
            "value": [{"id": "doc1", "vector": [0.1, 0.2, 0.3], "document_id": "doc1", "title": "Test Document"}]
        })

        with patch.object(openai_file_search_plugin, 'get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]

            result = await openai_file_search_plugin.call_search(query=query, index_name=index_name, result_count=5)
            search_results = json.loads(result)["search_results"]
            assert search_results[0]["id"] == "doc1"
            assert search_results[0]["@search.score"] == 1.0


@pytest.mark.asyncio
async def test_call_search_without_results(openai_file_search_plugin):
    query = "test query"
    index_name = "test_index"

    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.return_value = json.dumps({"value": []})  # Empty results

        result = await openai_file_search_plugin.call_search(query=query, index_name=index_name, result_count=5)
        assert json.loads(result) == {"search_results": []}


@pytest.mark.asyncio
async def test_handle_request(openai_file_search_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        
        event_label="message",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin",
        origin_plugin_name="origin_plugin_name"
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
async def test_call_search_error_handling(openai_file_search_plugin):
    with patch.object(openai_file_search_plugin.backend_internal_data_processing_dispatcher, 'read_data_content', new_callable=AsyncMock) as mock_read_data_content:
        mock_read_data_content.side_effect = Exception("Test error")
        result = await openai_file_search_plugin.call_search("query", "index_name", 5)
        assert json.loads(result) == {"error": "Failed to load search data."}


def test_validate_request(openai_file_search_plugin):
    event = IncomingNotificationDataBase(
        channel_id="channel_id",
        thread_id="thread_id",
        user_id="user_id",
        text="user text",
        timestamp="timestamp",
        
        event_label="message",
        response_id="response_id",
        user_name="user_name",
        user_email="user_email",
        is_mention=True,
        origin="origin",
        origin_plugin_name="origin_plugin_name"
    )
    assert openai_file_search_plugin.validate_request(event) == True

@pytest.mark.asyncio
async def test_handle_action_without_index_name(openai_file_search_plugin):
    action_input = ActionInput(action_name="search", parameters={"query": "test query"})
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    with patch.object(openai_file_search_plugin, 'call_search', new_callable=AsyncMock) as mock_call_search:
        mock_call_search.return_value = "search result"
        result = await openai_file_search_plugin.handle_action(action_input, mock_event)
        assert result == "search result"

        # Vérifier que le nom d'index par défaut de la configuration est utilisé
        default_index_name = openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_INDEX_NAME.lower()
        mock_call_search.assert_called_once_with(
            query="test query",
            index_name=default_index_name,
            result_count=openai_file_search_plugin.result_count,
            get_whole_doc=False
        )

@pytest.mark.asyncio
async def test_handle_action_with_empty_index_name_and_no_default(openai_file_search_plugin):
    # Supprimer temporairement le nom d'index par défaut de la configuration
    openai_file_search_plugin.openai_search_config.OPENAI_FILE_SEARCH_INDEX_NAME = ""

    action_input = ActionInput(action_name="search", parameters={"query": "test query"})
    mock_event = MagicMock(spec=IncomingNotificationDataBase)

    with pytest.raises(ValueError) as exc_info:
        await openai_file_search_plugin.handle_action(action_input, mock_event)

    assert str(exc_info.value) == "Index name is required but not provided."

@pytest.mark.asyncio
async def test_call_search_with_get_whole_doc(openai_file_search_plugin):
    query = "test query"
    index_name = "test_index"

    # Mock des données à retourner par read_data_content
    mock_file_content = json.dumps({
        "value": [
            {
                "id": "doc1_passage1",
                "vector": [0.1, 0.2, 0.3],
                "document_id": "doc1",
                "title": "Test Document",
                "passage_id": 1,
                "content": "Passage 1 content"
            },
            {
                "id": "doc1_passage2",
                "vector": [0.1, 0.2, 0.3],
                "document_id": "doc1",
                "title": "Test Document",
                "passage_id": 2,
                "content": "Passage 2 content"
            }
        ]
    })

    with patch.object(
        openai_file_search_plugin.backend_internal_data_processing_dispatcher,
        'read_data_content',
        new_callable=AsyncMock
    ) as mock_read_data_content:
        mock_read_data_content.return_value = mock_file_content

        with patch.object(openai_file_search_plugin, 'get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]

            result = await openai_file_search_plugin.call_search(
                query=query,
                index_name=index_name,
                result_count=5,
                get_whole_doc=True
            )
            search_results = json.loads(result)["search_results"]

            # Vérifier que le contenu est remplacé par le contenu complet du document
            assert len(search_results) == 2
            for res in search_results:
                assert res["content"] == "Passage 1 content Passage 2 content"

@pytest.mark.asyncio
async def test_fetch_full_document_content_error_handling(openai_file_search_plugin):
    document_id = "doc1"
    index_name = "test_index"

    with patch.object(
        openai_file_search_plugin.backend_internal_data_processing_dispatcher,
        'read_data_content',
        new_callable=AsyncMock
    ) as mock_read_data_content:
        mock_read_data_content.side_effect = Exception("Test error")

        # Même si une exception se produit, la méthode doit retourner une chaîne vide
        full_content = await openai_file_search_plugin.fetch_full_document_content(document_id, index_name)
        assert full_content == ""

@pytest.mark.asyncio
async def test_replace_with_full_document_content_error_handling(openai_file_search_plugin):
    search_results = [
        {
            "id": "doc1_passage1",
            "document_id": "doc1",
            "similarity": 0.9,
            "content": "Original content"
        }
    ]
    index_name = "test_index"

    with patch.object(
        openai_file_search_plugin,
        'fetch_full_document_content',
        new_callable=AsyncMock
    ) as mock_fetch_full_document_content:
        mock_fetch_full_document_content.side_effect = Exception("Test error")

        # La méthode doit gérer l'exception et retourner les résultats de recherche originaux
        results = await openai_file_search_plugin.replace_with_full_document_content(search_results, index_name)
        assert results == search_results

@pytest.mark.asyncio
async def test_trigger_genai(openai_file_search_plugin):
    with pytest.raises(NotImplementedError) as exc_info:
        openai_file_search_plugin.trigger_genai()

    assert "is not implemented" in str(exc_info.value)

def test_plugin_name_property(openai_file_search_plugin):
    # Test du getter
    assert openai_file_search_plugin.plugin_name == "openai_file_search"

    # Test du setter
    openai_file_search_plugin.plugin_name = "new_plugin_name"
    assert openai_file_search_plugin.plugin_name == "new_plugin_name"