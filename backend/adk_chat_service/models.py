"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User message to send to the LLM"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation ID for multi-turn conversations"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Override default temperature for this request"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=8192,
        description="Override default max tokens for this request"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Hello, how are you?",
                    "conversation_id": "conv-123",
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            ]
        }
    }


class ChatChunk(BaseModel):
    """Response model for streaming chat chunks."""

    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    content: str = Field(..., description="Text content of this chunk")
    done: bool = Field(..., description="Whether this is the final chunk")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (token count, timing, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chunk_id": "chunk-123",
                    "content": "Hello! How can I help you today?",
                    "done": False,
                    "metadata": None
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error type or category")
    detail: Optional[str] = Field(default=None, description="Detailed error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when error occurred"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "ADKClientError",
                    "detail": "Failed to initialize Google ADK client",
                    "timestamp": "2025-12-15T10:30:00Z"
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service status (healthy/degraded/unhealthy)")
    version: str = Field(..., description="Service version")
    adk_ready: bool = Field(..., description="Whether ADK client is initialized")
    kit_connected: bool = Field(default=False, description="Whether Kit extension is connected")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of health check"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "adk_ready": True,
                    "kit_connected": True,
                    "timestamp": "2025-12-15T10:30:00Z"
                }
            ]
        }
    }
