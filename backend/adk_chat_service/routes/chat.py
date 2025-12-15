"""Chat endpoint for streaming LLM responses."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .. import __version__
from ..models import ChatRequest, HealthResponse
from ..services.adk_client import ADKChatClient, get_adk_client
from ..services.stream_handler import format_stream_as_ndjson
from ..utils.exceptions import ADKClientError, StreamingError
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    adk_client: ADKChatClient = Depends(get_adk_client)
) -> StreamingResponse:
    """
    Stream chat responses from Google ADK.

    Accepts a chat message and streams the LLM response back as
    newline-delimited JSON (NDJSON) chunks.

    Args:
        request: Chat request with message and optional parameters
        adk_client: ADK client instance (injected)

    Returns:
        StreamingResponse with NDJSON content

    Raises:
        HTTPException: If streaming fails
    """
    try:
        logger.info(
            "Received chat request",
            message_length=len(request.message),
            conversation_id=request.conversation_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Get text stream from ADK client
        text_stream = adk_client.stream_chat(
            message=request.message,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            conversation_id=request.conversation_id
        )

        # Format as NDJSON stream
        ndjson_stream = format_stream_as_ndjson(
            text_stream,
            conversation_id=request.conversation_id
        )

        # Return streaming response
        return StreamingResponse(
            ndjson_stream,
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Content-Type-Options": "nosniff"
            }
        )

    except ADKClientError as e:
        logger.error(
            "ADK client error",
            error=e.message,
            detail=e.detail,
            conversation_id=request.conversation_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"ADK client error: {e.message}"
        )

    except StreamingError as e:
        logger.error(
            "Streaming error",
            error=e.message,
            detail=e.detail,
            conversation_id=request.conversation_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Streaming error: {e.message}"
        )

    except Exception as e:
        logger.error(
            "Unexpected error in chat endpoint",
            error=str(e),
            conversation_id=request.conversation_id
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    adk_client: ADKChatClient = Depends(get_adk_client)
) -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and whether ADK client is ready.

    Args:
        adk_client: ADK client instance (injected)

    Returns:
        HealthResponse with service status
    """
    try:
        adk_ready = adk_client.is_ready

        return HealthResponse(
            status="healthy" if adk_ready else "degraded",
            version=__version__,
            adk_ready=adk_ready
        )

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            version=__version__,
            adk_ready=False
        )
