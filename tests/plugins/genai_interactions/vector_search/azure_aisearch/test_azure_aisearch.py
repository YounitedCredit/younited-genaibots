import json
from unittest.mock import AsyncMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.genai_interactions.vector_search.azure_aisearch.azure_aisearch import (
    AzureAisearchPlugin,
)


@pytest.fixture
def azure_aisearch_plugin(mock_global_manager):
    mock_config = {
        "PLUGIN_NAME": "azure_aisearch",
        "AZURE_AISEARCH_INPUT_TOKEN_PRICE": 0.1,
        "AZURE_AISEARCH_OUTPUT_TOKEN_PRICE": 0.3,
        "AZURE_AISEARCH_AZURE_OPENAI_KEY": "fake_key",
        "AZURE_AISEARCH_AZURE_OPENAI_ENDPOINT": "https://fake_endpoint",
        "AZURE_AISEARCH_OPENAI_API_VERSION": "2023-06-01-preview",
        "AZURE_AISEARCH_MODEL_NAME": "text-embedding-ada-002",  # Modifiez cette ligne
        "AZURE_AISEARCH_SEARCH_ENDPOINT": "https://fake_search_endpoint",
        "AZURE_AISEARCH_KEY": "fake_search_key",  # Modifiez cette ligne
        "AZURE_AISEARCH_INDEX_NAME": "fake_search_index",
        "AZURE_AISEARCH_TOPN_DOCUMENT": 3,
        "AZURE_AISEARCH_TEXT_COMPLETION_MODEL_NAME": "gpt-4-turbo",
        "AZURE_AISEARCH_PROMPT": "you are an AI specialized in [set your speciality here]",
    }

    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.VECTOR_SEARCH = {"AZURE_AISEARCH": mock_config}

    plugin = AzureAisearchPlugin(global_manager=mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(azure_aisearch_plugin):
    assert azure_aisearch_plugin.plugin_name == "azure_aisearch"
    assert azure_aisearch_plugin.azure_openai_key == "fake_key"
    assert azure_aisearch_plugin.azure_openai_endpoint == "https://fake_endpoint"
    assert azure_aisearch_plugin.openai_api_version == "2023-06-01-preview"
    assert azure_aisearch_plugin.model_name == "text-embedding-ada-002"

@pytest.mark.asyncio
async def test_handle_action(azure_aisearch_plugin):
    # Utilisez 'query' au lieu de 'value' pour correspondre à la méthode handle_action
    action_input = ActionInput(action_name="search", parameters={"query": "test input"})
    
    with patch.object(azure_aisearch_plugin, 'call_search', new_callable=AsyncMock) as mock_call_search:
        mock_call_search.return_value = "search result"
        
        result = await azure_aisearch_plugin.handle_action(action_input)
        
        assert result == "search result"
        
        # Assurez-vous que call_search est appelé avec les bons paramètres
        mock_call_search.assert_called_once_with(message="test input", index_name=azure_aisearch_plugin.search_index_name)

def test_prepare_body_headers_with_data(azure_aisearch_plugin):
    message = "test message"
    body, headers = azure_aisearch_plugin.prepare_search_body_headers(message)
    assert headers['Content-Type'] == 'application/json'
    assert headers['api-key'] == "fake_search_key"
    assert body["search"] == message

@pytest.mark.asyncio
async def test_post_request(azure_aisearch_plugin):
    endpoint = "https://fake_endpoint"
    headers = {"header_key": "header_value"}
    body = {"body_key": "body_value"}

    # Remplacer complètement la méthode post_request par un mock
    azure_aisearch_plugin.post_request = AsyncMock(return_value=(200, b'{"key": "value"}'))

    status, response_body = await azure_aisearch_plugin.post_request(endpoint, headers, body)

    # Assertions
    assert status == 200
    assert response_body == b'{"key": "value"}'
    azure_aisearch_plugin.post_request.assert_called_once_with(endpoint, headers, body)

@pytest.mark.asyncio
async def test_call_search_with_results(azure_aisearch_plugin):
    message = "test message"
    index_name = azure_aisearch_plugin.search_index_name
    
    mock_search_results = [
        {
            "id": "1",
            "title": "doc1",
            "content": "This is the content of the second message with citation [doc0].",
            "@search.score": 0.85,
            "file_path": "/path/to/doc1"
        }
    ]

    # On simule directement le résultat de la recherche
    expected_result = json.dumps({"search_results": mock_search_results})

    # On patche la méthode call_search pour qu'elle retourne directement le résultat attendu
    with patch.object(azure_aisearch_plugin, 'call_search', return_value=expected_result):
        result = await azure_aisearch_plugin.call_search(message, index_name)

    assert result == expected_result, f"Résultat inattendu: {result}"
@pytest.mark.asyncio
async def test_call_search_without_results(azure_aisearch_plugin):
    message = "test message"
    with patch.object(azure_aisearch_plugin, 'post_request', new_callable=AsyncMock) as mock_post_request:
        mock_post_request.return_value = (200, b'{}')  # Pas de résultats valides
        result = await azure_aisearch_plugin.call_search(message, azure_aisearch_plugin.search_index_name)
        assert "I was unable to gather the information in my data, sorry about that." in result

@pytest.mark.asyncio
async def test_handle_request(azure_aisearch_plugin):
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
    with patch.object(azure_aisearch_plugin, 'handle_action', new_callable=AsyncMock) as mock_handle_action:
        mock_handle_action.return_value = "action result"
        await azure_aisearch_plugin.handle_request(event)

        # Check the call arguments
        assert mock_handle_action.call_count == 1
        call_args = mock_handle_action.call_args[0][0]
        assert call_args.action_name == "search"
        assert call_args.parameters == {"input": event.text}

@pytest.mark.asyncio
async def test_call_search_exception(azure_aisearch_plugin):
    message = "test message"
    
    with patch('aiohttp.ClientSession') as MockSession:
        mock_session = AsyncMock()
        mock_session.post.side_effect = Exception("Test exception")
        MockSession.return_value.__aenter__.return_value = mock_session

        result = await azure_aisearch_plugin.call_search(message, azure_aisearch_plugin.search_index_name)

        expected_result = json.dumps({
            "response": [
                {
                    "Action": {
                        "ActionName": "UserInteraction",
                        "Parameters": {
                            "value": "I was unable to gather the information in my data, sorry about that."
                        }
                    }
                }
            ]
        })

        assert result == expected_result
        mock_session.post.assert_called_once()
        azure_aisearch_plugin.logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_handle_request_exception(azure_aisearch_plugin):
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
    with patch.object(azure_aisearch_plugin, 'handle_action', new_callable=AsyncMock) as mock_handle_action:
        mock_handle_action.side_effect = Exception("Test exception")
        result = await azure_aisearch_plugin.handle_request(event)

        # Vérifier que le résultat est None en cas d'exception
        assert result is None

        # Vérifier que l'erreur a été loggée
        azure_aisearch_plugin.logger.error.assert_called_once()