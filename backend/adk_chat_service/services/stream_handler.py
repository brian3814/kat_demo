"""Stream processing utilities for handling ADK responses."""

import json
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from ..models import ChatChunk
from ..utils.exceptions import StreamingError
from ..utils.logger import get_logger

logger = get_logger()


async def format_stream_as_ndjson(
    stream: AsyncGenerator[str, None],
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Transform ADK text stream into NDJSON format.

    Converts raw text chunks into ChatChunk objects and serializes
    them as newline-delimited JSON for client consumption.

    Args:
        stream: Async generator yielding text chunks
        conversation_id: Optional conversation ID for tracking

    Yields:
        str: NDJSON formatted chat chunks (JSON + newline)

    Raises:
        StreamingError: If stream processing fails
    """
    try:
        chunk_count = 0

        # Stream text chunks
        async for text_chunk in stream:
            chunk_count += 1

            # Create ChatChunk model
            chat_chunk = ChatChunk(
                chunk_id=str(uuid.uuid4()),
                content=text_chunk,
                done=False,
                metadata={"chunk_number": chunk_count}
            )

            # Serialize to NDJSON (JSON + newline)
            yield chat_chunk.model_dump_json() + "\n"

        # Send completion chunk
        final_chunk = ChatChunk(
            chunk_id=str(uuid.uuid4()),
            content="",
            done=True,
            metadata={
                "chunk_number": chunk_count + 1,
                "total_chunks": chunk_count,
                "conversation_id": conversation_id
            }
        )
        yield final_chunk.model_dump_json() + "\n"

        logger.info(
            "Stream formatting completed",
            total_chunks=chunk_count,
            conversation_id=conversation_id
        )

    except Exception as e:
        logger.error(
            "Error formatting stream",
            error=str(e),
            conversation_id=conversation_id
        )
        # Send error chunk to client
        error_chunk = {
            "chunk_id": str(uuid.uuid4()),
            "content": "",
            "done": True,
            "error": str(e)
        }
        yield json.dumps(error_chunk) + "\n"

        raise StreamingError(
            message="Failed to format stream as NDJSON",
            detail=str(e)
        )


def add_stream_metadata(
    chunk: Dict[str, Any],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add metadata to a stream chunk.

    Args:
        chunk: Chat chunk dictionary
        metadata: Metadata to add (timing, tokens, etc.)

    Returns:
        Updated chunk with metadata
    """
    if chunk.get("metadata") is None:
        chunk["metadata"] = {}

    chunk["metadata"].update(metadata)
    return chunk


async def handle_stream_backpressure(
    stream: AsyncGenerator[str, None],
    max_buffer_size: int = 100
) -> AsyncGenerator[str, None]:
    """
    Handle backpressure in streaming responses.

    Implements basic buffering to handle slow consumers.

    Args:
        stream: Async generator yielding text chunks
        max_buffer_size: Maximum number of chunks to buffer

    Yields:
        str: Text chunks with backpressure handling

    Note:
        This is a basic implementation. For production, consider
        using more sophisticated flow control.
    """
    buffer = []

    try:
        async for chunk in stream:
            buffer.append(chunk)

            # Yield buffered chunks when buffer is full
            if len(buffer) >= max_buffer_size:
                for buffered_chunk in buffer:
                    yield buffered_chunk
                buffer.clear()

        # Yield remaining buffered chunks
        for buffered_chunk in buffer:
            yield buffered_chunk

    except Exception as e:
        logger.error("Error in backpressure handling", error=str(e))
        raise StreamingError(
            message="Backpressure handling failed",
            detail=str(e)
        )
