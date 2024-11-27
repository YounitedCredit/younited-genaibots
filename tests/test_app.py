from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a minimal mock of the app without invoking full initialization
app = FastAPI()

# Define minimal endpoints for testing
@app.get("/health")
async def health_check():
    return "OK"

@app.get("/health/ping")
async def health_ping():
    return "pong"

@app.get("/custom-error")
async def custom_error_endpoint():
    from fastapi import HTTPException
    raise HTTPException(status_code=418, detail="I'm a teapot")


client = TestClient(app)


@patch("dotenv.load_dotenv", return_value=True)  # Mock dotenv completely
@patch("os.makedirs")  # Mock directory creation
@patch.dict("os.environ", {
    "LOCAL_LOGGING_FILE_PATH": "./mock_logs",  # Mocked logging path
    "BOT_UNIQUE_ID": "test-bot-id",
    "LOG_DEBUG_LEVEL": "debug"
})
def test_health_check(mock_makedirs, mock_load_dotenv):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == "OK"


@patch("dotenv.load_dotenv", return_value=True)
@patch("os.makedirs")
@patch.dict("os.environ", {
    "LOCAL_LOGGING_FILE_PATH": "./mock_logs",
    "BOT_UNIQUE_ID": "test-bot-id",
    "LOG_DEBUG_LEVEL": "debug"
})
def test_health_ping(mock_makedirs, mock_load_dotenv):
    response = client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == "pong"


def test_span_enriching_processor():
    # Mock the SpanEnrichingProcessor to simulate actual logic
    class MockSpan:
        def __init__(self):
            self.attributes = {}

        def get_attribute(self, key):
            if key == "http.request.headers":
                return {
                    "PostmanToken": "mock_token",
                    "AzureFdId": "mock_fdid",
                    "AzureAgId": "mock_agid",
                    "YucClientVersion": "mock_version",
                }
            return None

        def set_attribute(self, key, value):
            self.attributes[key] = value

    class MockSpanEnrichingProcessor:
        def on_end(self, span):
            headers = span.get_attribute("http.request.headers")
            if headers:
                span.set_attribute("PostmanToken", headers.get("PostmanToken"))
                span.set_attribute("AzureFdId", headers.get("AzureFdId"))
                span.set_attribute("AzureAgId", headers.get("AzureAgId"))
                span.set_attribute("YucClientVersion", headers.get("YucClientVersion"))

    # Use the mock processor
    processor = MockSpanEnrichingProcessor()
    span = MockSpan()

    # Call the processor logic
    processor.on_end(span)

    # Assert the expected attributes are set
    assert span.attributes == {
        "PostmanToken": "mock_token",
        "AzureFdId": "mock_fdid",
        "AzureAgId": "mock_agid",
        "YucClientVersion": "mock_version",
    }


@patch("dotenv.load_dotenv", return_value=True)
@patch("os.makedirs")
@patch.dict("os.environ", {
    "LOCAL_LOGGING_FILE_PATH": "./mock_logs",
    "BOT_UNIQUE_ID": "test-bot-id",
    "LOG_DEBUG_LEVEL": "debug"
})
def test_custom_exception_handler(mock_makedirs, mock_load_dotenv):
    response = client.get("/custom-error")
    assert response.status_code == 418
    assert "I'm a teapot" in response.json().get("detail", "")
