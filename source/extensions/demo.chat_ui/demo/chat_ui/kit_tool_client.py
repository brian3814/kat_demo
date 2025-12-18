"""WebSocket client for connecting Kit to backend for tool execution."""

import asyncio
import json
import uuid
import carb
from typing import Dict, Any, Callable, Optional

from .usd_tools import USDTools


class KitToolClient:
    """
    WebSocket client that connects Kit to the backend.

    Receives tool call requests from the backend (JSON-RPC 2.0),
    executes them using USDTools, and sends results back.
    """

    def __init__(
        self,
        backend_url: str = "ws://localhost:8000/ws/tools",
        reconnect_delay: float = 2.0,
        max_reconnect_delay: float = 30.0
    ):
        """
        Initialize Kit tool client.

        Args:
            backend_url: WebSocket URL for backend connection
            reconnect_delay: Initial reconnection delay in seconds
            max_reconnect_delay: Maximum reconnection delay in seconds
        """
        self.backend_url = backend_url
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay

        self.websocket = None
        self.tools = USDTools()
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._current_delay = reconnect_delay

        # Tool registry mapping tool names to methods
        self.tool_registry: Dict[str, Callable] = {
            "raycast_from_camera": self.tools.raycast_from_camera,
            "get_selection": self.tools.get_selection,
            "get_prim_info": self.tools.get_prim_info,
            "get_camera_info": self.tools.get_camera_info,
            "create_prim": self.tools.create_prim,
            "list_all_prims": self.tools.list_all_prims,
        }

    async def start(self):
        """Start the WebSocket client and connect to backend."""
        self._running = True
        self._current_delay = self.reconnect_delay
        await self._connect()

    async def stop(self):
        """Stop the WebSocket client."""
        self._running = False

        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        carb.log_info("[Kit Tool Client] Stopped")

    async def _connect(self):
        """Establish WebSocket connection to backend."""
        try:
            import websockets

            carb.log_info(f"[Kit Tool Client] Connecting to {self.backend_url}")

            self.websocket = await websockets.connect(self.backend_url)
            self._current_delay = self.reconnect_delay  # Reset delay on successful connection

            carb.log_info("[Kit Tool Client] Connected to backend")

            # Send registration message with available tools
            await self._send_registration()

            # Start message handler
            asyncio.ensure_future(self._message_loop())

        except ImportError:
            carb.log_error("[Kit Tool Client] websockets package not available")
        except Exception as e:
            carb.log_warn(f"[Kit Tool Client] Connection failed: {e}")
            if self._running:
                self._schedule_reconnect()

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        if not self._running:
            return

        carb.log_info(f"[Kit Tool Client] Reconnecting in {self._current_delay}s...")

        async def reconnect():
            await asyncio.sleep(self._current_delay)
            # Exponential backoff
            self._current_delay = min(self._current_delay * 2, self.max_reconnect_delay)
            await self._connect()

        self._reconnect_task = asyncio.ensure_future(reconnect())

    async def _send_registration(self):
        """Send tool registration message to backend."""
        registration = {
            "jsonrpc": "2.0",
            "method": "kit.register",
            "params": {
                "tools": self._get_tool_schemas()
            }
        }

        await self._send(registration)
        carb.log_info("[Kit Tool Client] Sent tool registration")

    async def _message_loop(self):
        """Handle incoming messages from backend."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    carb.log_error(f"[Kit Tool Client] Invalid JSON: {e}")

        except Exception as e:
            carb.log_warn(f"[Kit Tool Client] Connection lost: {e}")
            self.websocket = None
            if self._running:
                self._schedule_reconnect()

    async def _handle_message(self, data: Dict[str, Any]):
        """
        Handle incoming JSON-RPC 2.0 message.

        Args:
            data: Parsed JSON-RPC message
        """
        # Check if it's a JSON-RPC 2.0 request (has method and id)
        if "method" in data and "id" in data:
            await self._handle_tool_call(data)
        elif "method" in data:
            # Notification (no id) - just log it
            carb.log_info(f"[Kit Tool Client] Received notification: {data.get('method')}")
        else:
            carb.log_warn(f"[Kit Tool Client] Unknown message format: {data}")

    async def _handle_tool_call(self, request: Dict[str, Any]):
        """
        Handle a tool call request from backend.

        Args:
            request: JSON-RPC 2.0 request with method, params, and id
        """
        method = request.get("method")
        params = request.get("params", {})
        call_id = request.get("id")

        carb.log_info(f"[Kit Tool Client] Tool call: {method} (id={call_id})")

        # Send status update
        await self._send_status(call_id, "running", f"Executing {method}...")

        try:
            if method not in self.tool_registry:
                # Method not found error
                await self._send_error(call_id, -32601, f"Method not found: {method}")
                return

            # Execute tool
            tool_func = self.tool_registry[method]

            if params:
                result = tool_func(**params)
            else:
                result = tool_func()

            # Send result
            await self._send_result(call_id, result)
            carb.log_info(f"[Kit Tool Client] Tool completed: {method} success={result.get('success', False)}")

        except TypeError as e:
            # Invalid params error
            await self._send_error(call_id, -32602, f"Invalid params: {str(e)}")
        except Exception as e:
            # Tool execution error
            carb.log_error(f"[Kit Tool Client] Tool error: {e}")
            await self._send_error(call_id, -32000, str(e))

    async def _send(self, data: Dict[str, Any]):
        """Send JSON message to backend."""
        if self.websocket:
            await self.websocket.send(json.dumps(data))

    async def _send_result(self, call_id: str, result: Dict[str, Any]):
        """Send successful tool result."""
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": call_id
        }
        await self._send(response)

    async def _send_error(self, call_id: str, code: int, message: str):
        """Send error response."""
        response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": call_id
        }
        await self._send(response)

    async def _send_status(self, call_id: str, status: str, message: str):
        """Send status update notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": "tool.status",
            "params": {
                "call_id": call_id,
                "status": status,
                "message": message
            }
        }
        await self._send(notification)

    def _get_tool_schemas(self) -> list:
        """
        Get tool schemas for registration.

        Returns:
            List of tool schemas in JSON Schema format
        """
        return [
            {
                "name": "raycast_from_camera",
                "description": "Perform raycast from the viewport camera center to find what prim is in the camera's view. Returns the closest prim the camera is pointing at.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_distance": {
                            "type": "number",
                            "description": "Maximum raycast distance in scene units",
                            "default": 1000.0
                        }
                    }
                }
            },
            {
                "name": "get_selection",
                "description": "Get the list of currently selected prims in the Omniverse viewport. Returns paths, names, and types of selected prims.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_prim_info",
                "description": "Get detailed information about a specific USD prim, including its attributes like position, rotation, scale, visibility, and color.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prim_path": {
                            "type": "string",
                            "description": "Full USD path to the prim (e.g., '/World/Cube')"
                        }
                    },
                    "required": ["prim_path"]
                }
            },
            {
                "name": "get_camera_info",
                "description": "Get information about the current viewport camera, including its position and direction in world space.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_prim",
                "description": "Create a new USD prim (3D object) in the scene. Supports Cube, Sphere, Cylinder, Cone, and Xform types.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prim_type": {
                            "type": "string",
                            "description": "Type of prim to create",
                            "enum": ["Cube", "Sphere", "Cylinder", "Cone", "Xform"]
                        },
                        "prim_path": {
                            "type": "string",
                            "description": "USD path for the new prim (e.g., '/World/MyCube')"
                        },
                        "position": {
                            "type": "array",
                            "description": "Optional [x, y, z] position",
                            "items": {"type": "number"}
                        }
                    },
                    "required": ["prim_type", "prim_path"]
                }
            },
            {
                "name": "list_all_prims",
                "description": "List all USD prims in the scene under a given root path. Useful for understanding scene hierarchy.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "root_path": {
                            "type": "string",
                            "description": "Root USD path to start listing from",
                            "default": "/"
                        }
                    }
                }
            }
        ]
