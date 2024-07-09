# FILEPATH: /e:/NEWREPOS/Yuc.GenAi.Bots.Framework/tests/test_app.py

from os import environ
from unittest.mock import Mock, create_autospec, patch

from dotenv import load_dotenv
from fastapi import HTTPException
from opentelemetry.trace import Span
from starlette.testclient import TestClient

from app import SpanEnrichingProcessor, app
from core.global_manager import GlobalManager

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == "OK"

def test_health_ping():
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == "pong"

@patch('utils.plugin_manager.plugin_manager.Plugins')
def test_http_exception_handler(mock_plugins):
    # Create a FastAPI TestClient
    client = TestClient(app)

    # Define a route that raises an HTTPException
    @app.get("/test_http_exception")
    async def raise_http_exception():
        raise HTTPException(status_code=400, detail="Test exception")

    # Make a request to the route
    response = client.get("/test_http_exception")

    # Check that the HTTPException was handled correctly
    assert response.status_code == 400
    assert response.json() == {"message": "HTTP Error: Test exception"}

def test_span_enriching_processor_on_end():
    # Create a SpanEnrichingProcessor and a mock span
    processor = SpanEnrichingProcessor()
    mock_span = create_autospec(Span)

    # Manually add the get_attribute method to the mock_span
    mock_span.get_attribute = Mock(return_value={'PostmanToken': 'test'})

    # Call on_end with the mock span
    processor.on_end(mock_span)

def test_load_dotenv():
    # Set some environment variables
    environ['TEST_VARIABLE'] = 'test value'

    # Call load_dotenv
    load_dotenv()

    # Check that the environment variables were loaded correctly
    assert environ['TEST_VARIABLE'] == 'test value'

def test_global_manager_init():
    # Create a mock app
    mock_app = Mock()

    # Create a GlobalManager
    global_manager = GlobalManager(mock_app)

    # Check that the GlobalManager was initialized correctly
    assert isinstance(global_manager, GlobalManager)
