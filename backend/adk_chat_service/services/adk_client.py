"""Google ADK client wrapper for LLM integration."""

import asyncio
from typing import AsyncGenerator, Optional

from google import genai
from google.genai.types import GenerateContentConfig, GenerateContentResponse

from ..config import Settings
from ..utils.exceptions import ADKClientError
from ..utils.logger import get_logger

logger = get_logger()


class ADKChatClient:
    """
    Wrapper around Google ADK for chat interactions.

    Implements singleton pattern for lifecycle management and provides
    async streaming interface for chat completions.
    """

    def __init__(self, settings: Settings):
        """
        Initialize ADK client with settings.

        Args:
            settings: Application settings with API key and model config
        """
        self.settings = settings
        self.client: Optional[genai.Client] = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize the Google ADK client.

        Creates the client with API key and verifies connectivity.

        Raises:
            ADKClientError: If initialization fails
        """
        async with self._lock:
            if self._initialized:
                logger.info("ADK client already initialized")
                return

            try:
                logger.info("Initializing Google ADK client", model=self.settings.model_name)

                # Initialize Google GenAI client
                self.client = genai.Client(api_key=self.settings.google_api_key)

                self._initialized = True
                logger.info("ADK client initialized successfully")

            except Exception as e:
                logger.error("Failed to initialize ADK client", error=str(e))
                raise ADKClientError(
                    message="Failed to initialize Google ADK client",
                    detail=str(e)
                )

    async def stream_chat(
        self,
        message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat responses from Google ADK.

        Args:
            message: User message to send to the LLM
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            conversation_id: Optional conversation ID for context (future use)

        Yields:
            str: Text chunks from the streaming response

        Raises:
            ADKClientError: If streaming fails
        """
        if not self._initialized or self.client is None:
            raise ADKClientError(
                message="ADK client not initialized",
                detail="Call initialize() before streaming"
            )

        try:
            # Use request parameters or fall back to defaults
            temp = temperature if temperature is not None else self.settings.temperature
            max_tok = max_tokens if max_tokens is not None else self.settings.max_tokens

            logger.info(
                "Starting chat stream",
                message_length=len(message),
                temperature=temp,
                max_tokens=max_tok,
                conversation_id=conversation_id
            )

            # Configure generation parameters
            config = GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_tok,
            )

            # Stream response from ADK
            response_stream = await asyncio.to_thread(
                self.client.models.generate_content_stream,
                model=self.settings.model_name,
                contents=message,
                config=config
            )

            # Yield text chunks as they arrive
            chunk_count = 0
            for chunk in response_stream:
                if chunk.text:
                    chunk_count += 1
                    yield chunk.text

            logger.info(
                "Chat stream completed",
                chunk_count=chunk_count,
                conversation_id=conversation_id
            )

        except Exception as e:
            logger.error(
                "Error during chat streaming",
                error=str(e),
                conversation_id=conversation_id
            )
            raise ADKClientError(
                message="Failed to stream chat response",
                detail=str(e)
            )

    async def shutdown(self) -> None:
        """
        Cleanup ADK client resources.

        Call this during application shutdown.
        """
        async with self._lock:
            if self._initialized:
                logger.info("Shutting down ADK client")
                # No explicit cleanup needed for genai.Client
                self.client = None
                self._initialized = False
                logger.info("ADK client shut down successfully")

    @property
    def is_ready(self) -> bool:
        """Check if ADK client is initialized and ready."""
        return self._initialized and self.client is not None

    def register_tool(self, tool) -> None:
        """
        Register a tool for function calling (Phase 2 - MCP integration).

        Args:
            tool: Tool instance to register

        Note:
            This is a placeholder for Phase 2 MCP tool integration.
        """
        logger.warning("Tool registration not yet implemented (Phase 2)")
        # TODO: Implement tool registration for MCP
        pass


# Global client instance
_adk_client: Optional[ADKChatClient] = None


def get_adk_client() -> ADKChatClient:
    """
    Get the global ADK client instance.

    Returns:
        ADKChatClient: Global client instance

    Raises:
        ADKClientError: If client not initialized
    """
    if _adk_client is None:
        raise ADKClientError(
            message="ADK client not initialized",
            detail="Client must be initialized during application startup"
        )
    return _adk_client


def set_adk_client(client: ADKChatClient) -> None:
    """Set the global ADK client instance."""
    global _adk_client
    _adk_client = client
