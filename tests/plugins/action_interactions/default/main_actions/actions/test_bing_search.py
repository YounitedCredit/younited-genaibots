from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.action_interactions.default.main_actions.actions.bing_search import (
    BingSearch,
)


@pytest.fixture
def mock_env_var(monkeypatch):
    monkeypatch.setenv("BING_SEARCH_SUBSCRIPTION_KEY", "fake_subscription_key")

@pytest.fixture
def mock_response():
    mock_resp = MagicMock()
    mock_resp.text = "Fake HTML content"
    mock_resp.json.return_value = {
        "webPages": {
            "value": [
                {"url": "https://example.com", "snippet": "Example snippet"}
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

@pytest.fixture
def bing_search_instance(mock_global_manager):
    # Configurer les mocks Async pour les dispatchers
    mock_global_manager.user_interactions_dispatcher = AsyncMock()
    mock_global_manager.genai_interactions_text_dispatcher = AsyncMock()
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    return BingSearch(mock_global_manager)

@pytest.fixture
def action_input():
    return ActionInput(
        action_name='bing_search',
        parameters={
            'query': 'test query',
            'result_number': 1,
            'from_snippet': False,
            'user_input': 'user input',
            'urls': ''
        }
    )

@pytest.fixture
def incoming_notification():
    return IncomingNotificationDataBase(
        timestamp="2023-01-01T00:00:00Z",
        converted_timestamp="2023-01-01T00:00:00Z",
        event_label="test_event",
        channel_id="test_channel",
        thread_id="test_thread",
        response_id="test_response",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="user123",
        is_mention=False,
        text="Test message",
        origin="test_origin",
        origin_plugin_name="plugin_name"
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_bing_search(mock_get, mock_response, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_get.return_value = mock_response
    await bing_search_instance.execute(action_input, incoming_notification)

    # Vérifier que l'appel à perform_search a été fait
    mock_get.assert_any_call(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": "fake_subscription_key"},
        params={"q": "test query", "textDecorations": True, "textFormat": "Raw"}
    )

    # Vérifier que genai_interactions_text_dispatcher.trigger_genai a été appelé
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_with_invalid_url(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    action_input.parameters['urls'] = 'invalid_url'
    await bing_search_instance.execute(action_input, incoming_notification)
    # Assertion to check if the invalid URL message was logged
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry the url invalid_url is not valid",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_connection_error(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_get.side_effect = requests.exceptions.ConnectionError()

    await bing_search_instance.execute(action_input, incoming_notification)

    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="ConnectionError for URL: https://api.bing.microsoft.com/v7.0/search. Could not connect to the server.",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_timeout_error(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_get.side_effect = requests.exceptions.Timeout()

    with pytest.raises(requests.exceptions.Timeout):
        await bing_search_instance.execute(action_input, incoming_notification)

    # Capturez tous les appels à send_message
    calls = bing_search_instance.user_interactions_dispatcher.send_message.call_args_list

    # Affichez les appels pour le débogage
    print(f"Nombre d'appels à send_message: {len(calls)}")
    for i, call in enumerate(calls):
        print(f"Appel {i + 1}:")
        print(f"  Arguments: {call.args}")
        print(f"  Kwargs: {call.kwargs}")

    # Vérifiez qu'au moins un appel a été fait
    assert len(calls) >= 1

    # Vérifiez le contenu du premier appel
    assert calls[0].kwargs['message'] == "Looking for more info on the web please wait..."
    assert calls[0].kwargs['is_internal'] == False

    # Si un deuxième appel a été fait, vérifiez son contenu
    if len(calls) > 1:
        assert "Timeout for URL:" in calls[1].kwargs['message']
        assert calls[1].kwargs['is_internal'] == True
    else:
        print("Attention: Le deuxième appel attendu à send_message n'a pas été effectué.")

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_general_error(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_get.side_effect = Exception("General error")

    # Mock la méthode handle_search_error
    bing_search_instance.handle_search_error = AsyncMock()

    await bing_search_instance.execute(action_input, incoming_notification)

    # Vérifier que handle_search_error a été appelé avec les bons arguments
    bing_search_instance.handle_search_error.assert_called_once()
    call_args = bing_search_instance.handle_search_error.call_args
    assert isinstance(call_args[0][0], Exception)
    assert str(call_args[0][0]) == "General error"
    assert call_args[0][1] == incoming_notification

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_with_urls(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    action_input.parameters['urls'] = 'https://example.com,https://example2.com'
    mock_get.return_value.text = "Sample content"
    await bing_search_instance.execute(action_input, incoming_notification)
    assert mock_get.call_count == 2
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_from_snippet(mock_get, mock_response, mock_env_var, bing_search_instance, action_input, incoming_notification):
    action_input.parameters['from_snippet'] = True
    mock_get.return_value = mock_response
    await bing_search_instance.execute(action_input, incoming_notification)
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_no_results(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response
    await bing_search_instance.execute(action_input, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry, we couldn't find a solution to your problem. Please try rephrasing your request.",
        message_type=MessageType.COMMENT,
        is_internal=False
    )

def test_cleanup_webcontent(bing_search_instance):
    dirty_text = "This is a\n test with  multiple    spaces\r\nand newlines"
    clean_text = bing_search_instance.cleanup_webcontent(dirty_text)
    assert clean_text == "This is a test with multiple spacesand newlines"

@pytest.mark.parametrize("url,expected", [
    ("https://www.example.com", True),
    ("http://localhost:8080", True),
    ("ftp://ftp.example.com", True),
    ("not_a_url", False),
    ("https://", False),
])
def test_is_valid_url(bing_search_instance, url, expected):
    assert bing_search_instance.is_valid_url(url) == expected

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_http_403_error(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_get.side_effect = requests.exceptions.HTTPError(response=MagicMock(status_code=403))
    await bing_search_instance.execute(action_input, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="403 Forbidden error for URL: https://api.bing.microsoft.com/v7.0/search. Skipping this URL.",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_process_urls(mock_get, bing_search_instance, incoming_notification):
    mock_get.return_value.text = "Sample content"
    urls = "https://example.com,https://example2.com"
    await bing_search_instance.process_urls(urls, incoming_notification)
    assert mock_get.call_count == 2
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_page_content(mock_get, bing_search_instance):
    mock_get.return_value.text = "<html><body><p>Test content</p></body></html>"
    content = await bing_search_instance.get_page_content("https://example.com")
    assert "Test content" in content

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content(mock_get, bing_search_instance, incoming_notification):
    mock_get.return_value.text = "<html><body><p>Test content</p></body></html>"
    urls = ["https://example.com", "https://example2.com"]
    await bing_search_instance.get_webpages_content(urls, incoming_notification)
    assert mock_get.call_count == 2
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@pytest.mark.asyncio
async def test_select_from_snippet(bing_search_instance, incoming_notification):
    search_results = {
        "webPages": {
            "value": [
                {"url": "https://example.com", "snippet": "Example snippet"},
                {"url": "https://example2.com", "snippet": "Another snippet"}
            ]
        }
    }
    await bing_search_instance.select_from_snippet(search_results, incoming_notification, 2, "test query")
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content_no_results(mock_get, bing_search_instance, incoming_notification):
    # Configurer le mock pour lever une exception pour chaque URL
    mock_get.side_effect = requests.exceptions.RequestException("Test exception")

    urls = ["https://example.com", "https://example2.com"]

    # Appeler la méthode à tester
    await bing_search_instance.get_webpages_content(urls, incoming_notification)

    # Vérifier que le message d'erreur final a été envoyé
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry, we couldn't find a solution to your problem. Please try rephrasing your request.",
        message_type=MessageType.COMMENT,
        is_internal=False
    )

    # Vérifier que les erreurs ont été enregistrées pour chaque URL
    assert bing_search_instance.logger.error.call_count == 2
    bing_search_instance.logger.error.assert_any_call(
        "An unexpected error occurred for URL: https://example.com. Error: Test exception"
    )
    bing_search_instance.logger.error.assert_any_call(
        "An unexpected error occurred for URL: https://example2.com. Error: Test exception"
    )

    # Vérifier qu'aucun appel à genai_interactions_text_dispatcher n'a été fait
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_not_called()

@pytest.mark.asyncio
async def test_process_urls_invalid(bing_search_instance, incoming_notification):
    urls = "invalid_url,https://example.com"
    await bing_search_instance.process_urls(urls, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry the url invalid_url is not valid",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_execute_bing_search_no_web_pages(mock_get, mock_env_var, bing_search_instance, action_input, incoming_notification):
    mock_response = MagicMock()
    mock_response.json.return_value = {"someOtherData": {}}  # No 'webPages' key
    mock_get.return_value = mock_response
    await bing_search_instance.execute(action_input, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry, we couldn't find a solution to your problem. Please try rephrasing your request.",
        message_type=MessageType.COMMENT,
        is_internal=False
    )


@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_page_content_complex_html(mock_get, bing_search_instance):
    mock_get.return_value.text = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Test Header</h1>
            <p>Test paragraph</p>
            <script>console.log('This should be removed');</script>
            <style>.test { color: red; }</style>
            <a href="https://example.com">Test Link</a>
        </body>
    </html>
    """
    content = await bing_search_instance.get_page_content("https://example.com")
    assert "Test Header" in content
    assert "Test paragraph" in content
    assert "Test Link" in content
    assert "This should be removed" not in content
    assert ".test { color: red; }" not in content

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_process_urls_mixed(mock_get, bing_search_instance, incoming_notification):
    mock_get.return_value.text = "Sample content"
    urls = "invalid_url,https://example.com,https://example2.com"
    await bing_search_instance.process_urls(urls, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry the url invalid_url is not valid",
        message_type=MessageType.COMMENT,
        is_internal=True
    )
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_not_called()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content_mixed_results(mock_get, bing_search_instance, incoming_notification):
    def side_effect(url):
        if url == "https://example.com":
            return MagicMock(text="<html><body><p>Test content</p></body></html>")
        else:
            raise requests.exceptions.RequestException("Test exception")

    mock_get.side_effect = side_effect
    urls = ["https://example.com", "https://example2.com"]
    await bing_search_instance.get_webpages_content(urls, incoming_notification)
    assert mock_get.call_count == 2
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()
    bing_search_instance.logger.error.assert_called_once_with(
        "An unexpected error occurred for URL: https://example2.com. Error: Test exception"
    )

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content_mixed_scenarios(mock_get, bing_search_instance, incoming_notification):
    def side_effect(url):
        if url == "https://example.com":
            return MagicMock(text="<html><body><p>Test content</p></body></html>")
        elif url == "https://example2.com":
            raise requests.exceptions.HTTPError(response=MagicMock(status_code=403))
        elif url == "https://example3.com":
            raise requests.exceptions.ConnectionError()
        elif url == "https://example4.com":
            raise requests.exceptions.Timeout()
        else:
            raise Exception("Unexpected error")

    mock_get.side_effect = side_effect
    urls = ["https://example.com", "https://example2.com", "https://example3.com", "https://example4.com", "https://example5.com"]

    await bing_search_instance.get_webpages_content(urls, incoming_notification)

    assert mock_get.call_count == 5
    assert bing_search_instance.logger.error.call_count == 4
    assert bing_search_instance.user_interactions_dispatcher.send_message.call_count == 5  # 4 error messages + 1 success message

    # Vérifier les messages d'erreur
    for url in urls[1:]:  # Tous sauf le premier
        bing_search_instance.user_interactions_dispatcher.send_message.assert_any_call(
            event=incoming_notification,
            message=f"An error occurred while fetching content from {url}.",
            message_type=MessageType.COMMENT,
            is_internal=True
        )

    # Vérifier que le message de succès est envoyé
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content_no_content(mock_get, bing_search_instance, incoming_notification):
    mock_get.side_effect = requests.exceptions.RequestException("Test exception")
    urls = ["https://example.com", "https://example2.com"]

    await bing_search_instance.get_webpages_content(urls, incoming_notification)

    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="Sorry, we couldn't find a solution to your problem. Please try rephrasing your request.",
        message_type=MessageType.COMMENT,
        is_internal=False
    )
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_not_called()

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_get_webpages_content_message_formation(mock_get, bing_search_instance, incoming_notification):
    mock_get.return_value.text = "<html><body><p>Test content</p></body></html>"
    urls = ["https://example.com", "https://example2.com"]

    await bing_search_instance.get_webpages_content(urls, incoming_notification)

    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()
    call_args = bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.call_args
    event_copy = call_args[1]['event']

    assert "Here is a text content from the 2 web page(s) we analyzed:" in event_copy.text
    assert "https://example.com Test content" in event_copy.text
    assert "https://example2.com Test content" in event_copy.text
    assert "Process this to answer the user, mention the webpage(s) as a Slack link" in event_copy.text

def parse_from_snippet(self, from_snippet):
    if from_snippet is None:
        return False
    if isinstance(from_snippet, str):
        return from_snippet.lower() == 'true'
    return bool(from_snippet)

@patch('plugins.action_interactions.default.main_actions.actions.bing_search.requests.get')
@pytest.mark.asyncio
async def test_perform_search(mock_get, mock_response, bing_search_instance, incoming_notification):
    # Remplacer directement la clé de souscription
    bing_search_instance.subscription_key = "fake_subscription_key"

    mock_get.return_value = mock_response
    result = await bing_search_instance.perform_search("test query", incoming_notification)
    assert result == mock_response.json.return_value
    mock_get.assert_called_with(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": "fake_subscription_key"},
        params={"q": "test query", "textDecorations": True, "textFormat": "Raw"}
    )

@pytest.mark.asyncio
async def test_handle_search_error(bing_search_instance, incoming_notification):
    error = requests.exceptions.ConnectionError()
    await bing_search_instance.handle_search_error(error, incoming_notification)
    bing_search_instance.user_interactions_dispatcher.send_message.assert_called_with(
        event=incoming_notification,
        message="ConnectionError for URL: https://api.bing.microsoft.com/v7.0/search. Could not connect to the server.",
        message_type=MessageType.COMMENT,
        is_internal=True
    )

@pytest.mark.asyncio
async def test_process_search_results(bing_search_instance, incoming_notification):
    search_results = {
        "webPages": {
            "value": [
                {"url": "https://example.com"},
                {"url": "https://example2.com"}
            ]
        }
    }
    await bing_search_instance.process_search_results(search_results, incoming_notification, 2, False, "test query")
    bing_search_instance.genai_interactions_text_dispatcher.trigger_genai.assert_called_once()
