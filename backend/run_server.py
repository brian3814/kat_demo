#!/usr/bin/env python
"""
FastAPI Backend Server Launcher for ADK Chat Service.

This script launches the uvicorn server with configuration from environment.
"""

import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    import uvicorn
    from adk_chat_service.config import get_settings
    from adk_chat_service.utils.logger import get_logger

    # Load settings
    settings = get_settings()
    logger = get_logger()

    def main():
        """Launch the uvicorn server."""
        logger.info(
            "Starting ADK Chat Service server",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level
        )

        # SECURITY WARNING: reload=True is for DEVELOPMENT ONLY
        # Set reload=False for production to prevent exposing file paths in errors
        uvicorn.run(
            "adk_chat_service.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,  # Enable hot reload for development
            log_level=settings.log_level.lower(),
            access_log=True
        )

    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"Failed to start server: {e}", file=sys.stderr)
    print("\nPlease ensure you have:", file=sys.stderr)
    print("1. Created a .env file with GOOGLE_API_KEY", file=sys.stderr)
    print("2. Installed dependencies: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)
