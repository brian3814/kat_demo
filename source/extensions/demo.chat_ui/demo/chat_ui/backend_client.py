"""Backend HTTP client for streaming chat responses."""

import aiohttp
import json
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
import carb


class BackendClient:
    """Async HTTP client for communicating with FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the backend client.

        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session is created (lazy initialization)."""
        async with self._lock:
            if self.session is None or self.session.closed:
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def health_check(self) -> bool:
        """Check if backend is available.

        Returns:
            True if backend is healthy, False otherwise
        """
        try:
            session = await self._ensure_session()
            async with session.get(f"{self.base_url}/api/v1/health") as response:
                return response.status == 200
        except Exception as e:
            carb.log_warn(f"Backend health check failed: {e}")
            return False

    async def stream_chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        conversation_history: Optional[list] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses from backend.

        Args:
            message: User message to send
            temperature: Model temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            conversation_history: Optional list of previous messages

        Yields:
            Dict containing:
                - content (str): Text content chunk
                - done (bool): Whether streaming is complete
                - chunk_id (int): Chunk sequence number
                - error (str, optional): Error message if any
        """
        session = await self._ensure_session()

        payload = {
            "message": message,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if conversation_history:
            payload["conversation_history"] = conversation_history

        try:
            async with session.post(
                f"{self.base_url}/api/v1/chat/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    carb.log_error(f"Backend error {response.status}: {error_text}")
                    yield {
                        "content": "",
                        "done": True,
                        "chunk_id": -1,
                        "error": f"Backend returned status {response.status}: {error_text}"
                    }
                    return

                # Read NDJSON stream line by line
                chunk_id = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Add chunk_id if not present
                        if "chunk_id" not in data:
                            data["chunk_id"] = chunk_id
                            chunk_id += 1

                        yield data

                        # Stop if streaming is complete
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError as e:
                        carb.log_warn(f"Failed to parse JSON line: {line}, error: {e}")
                        continue

        except aiohttp.ClientError as e:
            carb.log_error(f"HTTP request failed: {e}")
            yield {
                "content": "",
                "done": True,
                "chunk_id": -1,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            carb.log_error(f"Unexpected error during streaming: {e}")
            yield {
                "content": "",
                "done": True,
                "chunk_id": -1,
                "error": f"Unexpected error: {str(e)}"
            }

    async def send_chat(
        self,
        message: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        conversation_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """Send chat message and collect complete response (non-streaming).

        Args:
            message: User message to send
            temperature: Model temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            conversation_history: Optional list of previous messages

        Returns:
            Dict containing complete response with 'content' and 'error' fields
        """
        full_content = []
        error = None

        async for chunk in self.stream_chat(message, temperature, max_tokens, conversation_history):
            if chunk.get("error"):
                error = chunk["error"]
                break

            content = chunk.get("content", "")
            if content:
                full_content.append(content)

        return {
            "content": "".join(full_content),
            "error": error
        }
