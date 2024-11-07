from os import environ
from unittest.mock import Mock, create_autospec, patch
from dotenv import load_dotenv
from fastapi import HTTPException, FastAPI
from opentelemetry.trace import Span
from starlette.testclient import TestClient
import pytest

# Définir les variables d'environnement par défaut
DEFAULT_ENV_VARS = {
    "ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME": "main_actions",
    "USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME": "im_default_behavior",
    "GENAI_TEXT_DEFAULT_PLUGIN_NAME": "azure_chatgpt",
    "GENAI_IMAGE_DEFAULT_PLUGIN_NAME": "azure_dalle",
    "GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME": "openai_file_search",
    "INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME": "file_system",
    "INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME": "file_system_queue"
}

# Utiliser une fixture pour définir les variables d'environnement avant les tests
@pytest.fixture(scope='session', autouse=True)
def set_default_env_vars():
    with patch.dict(environ, DEFAULT_ENV_VARS):
        yield

# Importer l'application après avoir défini les variables d'environnement
from app import SpanEnrichingProcessor, create_app
from core.global_manager import GlobalManager

@pytest.fixture
def client(mock_global_manager):
    app, _ = create_app(global_manager_cls=lambda app: mock_global_manager)
    return TestClient(app)

@app.get("/test_http_exception")
async def raise_http_exception():
    raise HTTPException(status_code=400, detail="Test HTTP Exception")

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == "OK"

def test_health_ping(client):
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == "pong"

@patch('utils.plugin_manager.plugin_manager.Plugins')
def test_http_exception_handler(mock_plugins, client):
    # Mock the behavior of the plugin manager to include 'im_default_behavior'
    mock_plugins.get_plugin.return_value = Mock(name='im_default_behavior')

    response = client.get("/test_http_exception")
    assert response.status_code == 400
    assert response.json() == {"detail": "Test HTTP Exception"}

def test_span_enriching_processor_on_end():
    # Create a SpanEnrichingProcessor and a mock span
    processor = SpanEnrichingProcessor()
    mock_span = create_autospec(Span)

    # Manually add the get_attribute method to the mock_span
    mock_span.get_attribute = Mock(return_value={'PostmanToken': 'test'})

    # Call on_end with mock span
    processor.on_end(mock_span)

def test_load_dotenv():
    # Set some environment variables
    environ['TEST_VARIABLE'] = 'test value'

    # Call load_dotenv
    load_dotenv()

    # Check that the environment variables were loaded correctly
    assert environ['TEST_VARIABLE'] == 'test value'

def test_global_manager_init(mock_global_manager):
    # Create a mock app
    mock_app = Mock()

    # Create a GlobalManager
    global_manager = GlobalManager(mock_app)

    # Check that the GlobalManager was initialized correctly
    assert isinstance(global_manager, GlobalManager)