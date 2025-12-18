"""Kit WebSocket connection manager for tool execution."""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class PendingCall:
    """Represents a pending tool call waiting for result."""
    call_id: str
    tool_name: str
    future: asyncio.Future
    status_callback: Optional[Callable[[str, str, str], None]] = None


class KitConnectionManager:
    """
    Manages WebSocket connection to Kit extension.

    Handles tool registration, tool calls, and result routing.
    Implements JSON-RPC 2.0 protocol for communication.
    """

    def __init__(self):
        """Initialize the connection manager."""
        self.websocket = None
        self.registered_tools: List[Dict[str, Any]] = []
        self.pending_calls: Dict[str, PendingCall] = {}
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if Kit is connected."""
        return self._connected and self.websocket is not None

    async def register_connection(self, websocket) -> None:
        """
        Register a new Kit WebSocket connection.

        Args:
            websocket: WebSocket connection from Kit
        """
        async with self._lock:
            self.websocket = websocket
            self._connected = True
            logger.info("Kit connected to backend")

    async def unregister_connection(self) -> None:
        """Unregister Kit connection."""
        async with self._lock:
            self.websocket = None
            self._connected = False
            self.registered_tools = []

            # Fail all pending calls
            for call_id, pending in self.pending_calls.items():
                if not pending.future.done():
                    pending.future.set_exception(
                        ConnectionError("Kit disconnected while waiting for result")
                    )
            self.pending_calls.clear()

            logger.info("Kit disconnected from backend")

    def register_tools(self, tools: List[Dict[str, Any]]) -> None:
        """
        Register tools received from Kit.

        Args:
            tools: List of tool schemas
        """
        self.registered_tools = tools
        logger.info(f"Registered {len(tools)} tools from Kit", tools=[t.get("name") for t in tools])

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get registered tool schemas.

        Returns:
            List of tool schemas for ADK registration
        """
        return self.registered_tools

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        status_callback: Optional[Callable[[str, str, str], None]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Call a tool on the Kit side and wait for result.

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters
            status_callback: Optional callback for status updates (call_id, status, message)
            timeout: Timeout in seconds

        Returns:
            Tool execution result

        Raises:
            ConnectionError: If Kit is not connected
            TimeoutError: If tool execution times out
            Exception: If tool execution fails
        """
        if not self.is_connected:
            raise ConnectionError("Kit is not connected")

        call_id = f"call-{uuid.uuid4().hex[:8]}"
        future = asyncio.get_event_loop().create_future()

        # Register pending call
        self.pending_calls[call_id] = PendingCall(
            call_id=call_id,
            tool_name=tool_name,
            future=future,
            status_callback=status_callback
        )

        logger.info(f"Calling tool: {tool_name}", call_id=call_id, params=parameters)

        try:
            # Send JSON-RPC 2.0 request
            request = {
                "jsonrpc": "2.0",
                "method": tool_name,
                "params": parameters,
                "id": call_id
            }

            await self.websocket.send_text(json.dumps(request))

            # Wait for result with timeout
            result = await asyncio.wait_for(future, timeout=timeout)

            logger.info(f"Tool completed: {tool_name}", call_id=call_id, success=result.get("success"))
            return result

        except asyncio.TimeoutError:
            logger.error(f"Tool timeout: {tool_name}", call_id=call_id)
            raise TimeoutError(f"Tool {tool_name} timed out after {timeout}s")

        finally:
            # Clean up pending call
            self.pending_calls.pop(call_id, None)

    async def handle_message(self, message: str) -> None:
        """
        Handle incoming message from Kit.

        Args:
            message: Raw JSON message string
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Kit: {e}")
            return

        # Check message type
        if "method" in data:
            await self._handle_notification(data)
        elif "result" in data or "error" in data:
            await self._handle_response(data)
        else:
            logger.warn(f"Unknown message format from Kit: {data}")

    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """Handle JSON-RPC notification (no id)."""
        method = data.get("method")
        params = data.get("params", {})

        if method == "kit.register":
            # Tool registration
            tools = params.get("tools", [])
            self.register_tools(tools)

        elif method == "tool.status":
            # Status update
            call_id = params.get("call_id")
            status = params.get("status")
            message = params.get("message", "")

            pending = self.pending_calls.get(call_id)
            if pending and pending.status_callback:
                pending.status_callback(call_id, status, message)

            logger.debug(f"Tool status: {status}", call_id=call_id, message=message)

        else:
            logger.warn(f"Unknown notification method: {method}")

    async def _handle_response(self, data: Dict[str, Any]) -> None:
        """Handle JSON-RPC response (has id)."""
        call_id = data.get("id")

        if not call_id:
            logger.warn("Response missing id field")
            return

        pending = self.pending_calls.get(call_id)
        if not pending:
            logger.warn(f"No pending call for id: {call_id}")
            return

        if pending.future.done():
            logger.warn(f"Future already resolved for: {call_id}")
            return

        if "error" in data:
            # Error response
            error = data["error"]
            error_msg = f"Tool error ({error.get('code')}): {error.get('message')}"
            pending.future.set_exception(Exception(error_msg))

        else:
            # Success response
            result = data.get("result", {})
            pending.future.set_result(result)


# Global connection manager instance
_kit_manager: Optional[KitConnectionManager] = None


def get_kit_manager() -> KitConnectionManager:
    """
    Get the global Kit connection manager.

    Returns:
        KitConnectionManager instance
    """
    global _kit_manager
    if _kit_manager is None:
        _kit_manager = KitConnectionManager()
    return _kit_manager
