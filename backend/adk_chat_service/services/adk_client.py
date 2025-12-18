"""Google ADK client with Runner and InMemorySessionService for context management.

Uses ADK Agent + Runner pattern for chat with session-based context.
"""

import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, Callable

from ..config import Settings
from ..utils.exceptions import ADKClientError
from ..utils.logger import get_logger
from .session_manager import get_session_manager
from .adk_agent import create_omniverse_agent, OmniverseAgent

logger = get_logger()


class ADKChatClient:
    """
    ADK Chat Client using Runner with InMemorySessionService.

    Provides async streaming interface for chat completions with
    session-based context management and tool support.
    """

    def __init__(self, settings: Settings):
        """
        Initialize ADK client with settings.

        Args:
            settings: Application settings with API key and model config
        """
        self.settings = settings
        self._agent: Optional[OmniverseAgent] = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize the ADK client with Runner and session service.

        Raises:
            ADKClientError: If initialization fails
        """
        async with self._lock:
            if self._initialized:
                logger.info("ADK client already initialized")
                return

            try:
                logger.info(
                    "Initializing ADK client with Runner mode",
                    model=self.settings.model_name
                )

                # Ensure session manager is initialized
                get_session_manager()

                # Create and initialize the OmniverseAgent with Runner
                self._agent = await create_omniverse_agent(self.settings)

                self._initialized = True
                logger.info("ADK client initialized successfully")

            except Exception as e:
                logger.error("Failed to initialize ADK client", error=str(e))
                raise ADKClientError(
                    message="Failed to initialize ADK client",
                    detail=str(e)
                )

    async def stream_chat_with_tools(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: str = "default_user",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat responses with tool calling support using Runner.

        Args:
            message: User message to send to the LLM
            conversation_id: Optional session ID for continuing a conversation
            user_id: User identifier for session management
            temperature: Optional temperature override (not used in Runner mode)
            max_tokens: Optional max tokens override (not used in Runner mode)
            status_callback: Optional callback for status updates

        Yields:
            Dict with event type and data:
                - {"type": "text_delta", "content": str, "done": bool}
                - {"type": "tool_call", "tool": str, "params": dict}
                - {"type": "tool_result", "tool": str, "result": dict}
                - {"type": "error", "error": str}
                - {"type": "end", "done": True, "session_id": str}

        Raises:
            ADKClientError: If chat fails
        """
        if not self._initialized or self._agent is None:
            raise ADKClientError(
                message="ADK client not initialized",
                detail="Call initialize() before streaming"
            )

        try:
            logger.info(
                "Starting chat with Runner",
                message_length=len(message),
                user_id=user_id,
                session_id=conversation_id
            )

            # Stream events from the agent
            async for event in self._agent.run_conversation(
                message=message,
                user_id=user_id,
                session_id=conversation_id,
            ):
                yield event

        except Exception as e:
            logger.error(
                "Error during chat streaming",
                error=str(e),
                conversation_id=conversation_id
            )
            yield {
                "type": "error",
                "error": str(e),
                "done": True
            }

    async def stream_chat(
        self,
        message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat responses (text-only interface).

        Args:
            message: User message to send to the LLM
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            conversation_id: Optional conversation ID for context

        Yields:
            str: Text chunks from the streaming response

        Raises:
            ADKClientError: If streaming fails
        """
        async for event in self.stream_chat_with_tools(
            message=message,
            temperature=temperature,
            max_tokens=max_tokens,
            conversation_id=conversation_id
        ):
            if event.get("type") == "text_delta":
                yield event.get("content", "")

    async def shutdown(self) -> None:
        """Cleanup ADK client resources."""
        async with self._lock:
            if self._initialized:
                logger.info("Shutting down ADK client")
                if self._agent:
                    await self._agent.shutdown()
                    self._agent = None
                self._initialized = False
                logger.info("ADK client shut down successfully")

    @property
    def is_ready(self) -> bool:
        """Check if ADK client is initialized and ready."""
        return self._initialized and self._agent is not None and self._agent.is_ready


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
