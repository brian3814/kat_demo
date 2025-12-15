"""Extension entry point for Chat UI."""

import asyncio
import omni.ext
import omni.ui as ui
import carb

from .chat_window import ChatWindow


class ChatUIExtension(omni.ext.IExt):
    """Chat UI Extension for Omniverse Kit."""

    def __init__(self):
        """Initialize extension."""
        super().__init__()
        self._window: ChatWindow = None

    def on_startup(self, ext_id: str):
        """Called when extension starts.

        Args:
            ext_id: Extension ID
        """
        carb.log_info("[demo.chat_ui] Extension startup")

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
