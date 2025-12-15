"""CORS middleware configuration for Omniverse extension communication."""

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import Settings
from ..utils.logger import get_logger

logger = get_logger()


def setup_cors(app: FastAPI, settings: Settings) -> None:
    """
    Configure CORS middleware for the FastAPI application.

    Allows Omniverse Kit extensions running locally to communicate
    with the backend server.

    Args:
        app: FastAPI application instance
        settings: Application settings with CORS origins

    Note:
        For production deployment, restrict origins to specific domains
        instead of using wildcards.
    """
    # Process wildcard patterns in origins
    # FastAPI CORSMiddleware doesn't support wildcards in port numbers
    # For local development, we allow all localhost ports
    origins = []
    for origin in settings.cors_origins:
        if "*" in origin:
            # For development, allow common localhost patterns
            origins.extend([
                "http://localhost:8000",
                "http://localhost:8080",
                "http://localhost:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:3000",
            ])
        else:
            origins.append(origin)

    # Remove duplicates
    origins = list(set(origins))

    logger.info("Configuring CORS", origins=origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,  # Cache preflight requests for 10 minutes
    )

    logger.info("CORS middleware configured successfully")


# Production CORS configuration notes:
#
# For production deployment, use more restrictive CORS settings:
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://yourdomain.com",
#         "https://app.yourdomain.com"
#     ],
#     allow_credentials=True,
#     allow_methods=["POST"],  # Only allow necessary methods
#     allow_headers=["Content-Type", "Authorization"],  # Specific headers only
#     expose_headers=["Content-Type"],
#     max_age=3600,
# )
