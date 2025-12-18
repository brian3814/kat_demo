"""FastAPI application for ADK Chat Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .config import get_settings
from .middleware.cors import setup_cors
from .routes import chat, websocket
from .services.adk_client import ADKChatClient, set_adk_client
from .utils.exceptions import BackendError
from .utils.logger import get_logger, setup_logging

# Initialize settings
settings = get_settings()

# Setup logging
setup_logging(log_level=settings.log_level, log_file=settings.log_file)
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.

    Handles initialization and cleanup of resources like the ADK client.
    """
    # Startup
    logger.info("Starting ADK Chat Service", version=__version__)

    try:
        # Initialize ADK client
        adk_client = ADKChatClient(settings)
        await adk_client.initialize()
        set_adk_client(adk_client)

        logger.info("ADK Chat Service started successfully")
        yield

    except Exception as e:
        logger.error("Failed to start ADK Chat Service", error=str(e))
        raise

    finally:
        # Shutdown
        logger.info("Shutting down ADK Chat Service")

        try:
            # Cleanup ADK client
            from .services.adk_client import get_adk_client
            adk_client = get_adk_client()
            await adk_client.shutdown()
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

        logger.info("ADK Chat Service shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="ADK Chat Service",
    description="FastAPI backend for Google ADK chat integration with MCP extensibility",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup CORS middleware
setup_cors(app, settings)

# Register routes
app.include_router(chat.router)
app.include_router(websocket.router)


@app.exception_handler(BackendError)
async def backend_error_handler(request: Request, exc: BackendError):
    """
    Global exception handler for BackendError and subclasses.

    Converts custom exceptions to proper HTTP responses.
    """
    logger.error(
        "Backend error",
        error=exc.message,
        detail=exc.detail,
        path=request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "detail": exc.detail
        }
    )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ADK Chat Service",
        "version": __version__,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity checks."""
    return {"ping": "pong"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "adk_chat_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )
