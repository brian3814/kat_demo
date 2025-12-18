"""Extension entry point for Chat UI."""

import asyncio
import omni.ext
import omni.ui as ui
import carb
import carb.settings

from .chat_window import ChatWindow
from .kit_tool_client import KitToolClient


class ChatUIExtension(omni.ext.IExt):
    """Chat UI Extension for Omniverse Kit."""

    def __init__(self):
        """Initialize extension."""
        super().__init__()
        self._window: ChatWindow = None
        self._tool_client: KitToolClient = None

    def on_startup(self, ext_id: str):
        """Called when extension starts.

        Args:
            ext_id: Extension ID
        """
        carb.log_info("[demo.chat_ui] Extension startup")

        # Get settings
        settings = carb.settings.get_settings()
        backend_url = settings.get("/exts/demo.chat_ui/backend_url") or "http://localhost:8000"

        # Convert HTTP URL to WebSocket URL for tool client
        ws_url = backend_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_tools_url = f"{ws_url}/ws/tools"

        # Start Kit Tool Client (connects to backend as WebSocket client)
        self._tool_client = KitToolClient(backend_url=ws_tools_url)
        asyncio.ensure_future(self._tool_client.start())

        # Create chat window
        self._window = ChatWindow(title="LLM Chat", width=500, height=600)

        # Check backend health on startup (delayed to allow UI to build)
        async def delayed_check():
            await asyncio.sleep(0.1)  # Wait for UI to build
            await self._check_backend()
        asyncio.ensure_future(delayed_check())

        # Register window menu
        ui.Workspace.set_show_window_fn(
            "LLM Chat",
            lambda visible: self._set_window_visibility(visible)
        )

        carb.log_info("[demo.chat_ui] Extension started successfully")

    def on_shutdown(self):
        """Called when extension shuts down."""
        carb.log_info("[demo.chat_ui] Extension shutdown")

        # Stop tool client
        if self._tool_client:
            asyncio.ensure_future(self._tool_client.stop())
            self._tool_client = None

        # Clean up window
        if self._window:
            self._window.destroy()
            self._window = None

        # Unregister window menu
        ui.Workspace.set_show_window_fn("LLM Chat", None)

        carb.log_info("[demo.chat_ui] Extension shutdown complete")

    async def _check_backend(self):
        """Check backend health on startup."""
        if self._window:
            await self._window.check_backend_health()

    def _set_window_visibility(self, visible: bool):
        """Set chat window visibility.

        Args:
            visible: Whether window should be visible
        """
        if self._window:
            self._window.visible = visible
