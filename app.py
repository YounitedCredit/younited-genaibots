from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import SpanProcessor
from starlette.responses import JSONResponse
from uvicorn import run as uvicorn_run

from core.global_manager import GlobalManager


class SpanEnrichingProcessor(SpanProcessor):
    def on_end(self, span):
        headers = span.get_attribute('http.request.headers')
        is_from_postman = 'PostmanToken' in headers
        is_from_front_door = 'AzureFdId' in headers
        is_from_app_gateway = 'AzureAgId' in headers
        client_version = headers.get('YucClientVersion', '')
        custom_dimensions = {
            'IsFromPostman': is_from_postman,
            'IsFromFrontDoor': is_from_front_door,
            'IsFromAppGateway': is_from_app_gateway,
            'ClientVersion': client_version
        }
        for key, value in custom_dimensions.items():
            span.set_attribute(key, value)

# Initialize FastAPI application

def create_app():
    app = FastAPI()

    # Load environment variables
    load_dotenv()

    global_manager = GlobalManager(app=app)

    # Instrument the FastAPI application
    FastAPIInstrumentor.instrument_app(app)
    logger = global_manager.logger
    logger.info("Global manager initialized.")
    return app, logger

app, logger = create_app()

# Load environment variables
load_dotenv()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"HTTP Error: {exc.detail}"},
    )

@app.get("/health")
async def health_check():
    return "OK"

@app.get("/health/ping")
async def health_ping():
    return "pong"

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"Unhandled Exception: {str(exc)}"},
    )

if __name__ == "__main__":
    logger.info("Starting application...")
    uvicorn_run(app, host="0.0.0.0", port=7071)
    logger.info("Application started.")
