"""Main chat window UI."""

import asyncio
import omni.ui as ui
import carb
import carb.settings
from typing import List, Dict, Any

from .backend_client import BackendClient
from .message_widget import MessageWidget, StatusIndicator, ToolCallWidget


class ChatWindow(ui.Window):
    """Main chat window with streaming message support."""

    def __init__(self, title: str = "LLM Chat", width: int = 500, height: int = 600):
        """Initialize chat window.

        Args:
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
        """
        super().__init__(title, width=width, height=height)

        # Get settings
        settings = carb.settings.get_settings()
        backend_url = settings.get("/exts/demo.chat_ui/backend_url") or "http://localhost:8000"
        self.default_temperature = settings.get("/exts/demo.chat_ui/default_temperature") or 0.7
        self.default_max_tokens = settings.get("/exts/demo.chat_ui/default_max_tokens") or 2048

        # Initialize backend client
        self.client = BackendClient(base_url=backend_url)

        # Message tracking
        self.messages: List[MessageWidget] = []
        self.conversation_history: List[Dict[str, str]] = []

        # UI components
        self._message_container: ui.VStack = None
        self._input_field: ui.StringField = None
        self._send_button: ui.Button = None
        self._status_indicator: StatusIndicator = None
        self._scroll_frame: ui.ScrollingFrame = None

        # Streaming state
        self._is_streaming = False
        self._current_assistant_message: MessageWidget = None
        self._tool_widgets: Dict[str, ToolCallWidget] = {}  # call_id -> widget

        # Build UI
        self.frame.set_build_fn(self._build_ui)

    def _build_ui(self):
        """Build the chat window UI."""
        with self.frame:
            with ui.VStack(spacing=5, height=ui.Percent(100)):
                # Status indicator
                self._status_indicator = StatusIndicator()
                self._status_indicator.build()

                # Message history (scrollable)
                self._scroll_frame = ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED
                )
                with self._scroll_frame:
                    self._message_container = ui.VStack(spacing=10)


                # Input area
                with ui.VStack(spacing=5, height=ui.Percent(15)):
                    ui.Line(style={"color": ui.color(0.5, 0.5, 0.5, 1.0)})
                    with ui.HStack(spacing=5, height=ui.Fraction(1)):
                        ui.Spacer(width=5)
                        
                        # Multiline input field
                        self._input_field = ui.StringField(
                            multiline=True,
                            style={"font_size": 16}
                        )
                        self._input_field.model.add_end_edit_fn(self._on_input_submit)

                        # Send button
                        self._send_button = ui.Button(
                            "Send",
                            width=ui.Pixel(80),
                            clicked_fn=self._on_send_clicked,
                            style={"Button": {"background_color": ui.color(0.2, 0.6, 0.8, 1.0)}}
                        )
                        
                        ui.Spacer(width=5)
                
    def _on_input_submit(self, model):
        """Handle Enter key press in input field."""
        # Note: StringField's end_edit is called on focus loss, not Enter in multiline
        # For Enter key handling in multiline, we rely on the Send button
        pass

    def _on_send_clicked(self):
        """Handle send button click."""
        message = self._input_field.model.get_value_as_string().strip()

        if not message or self._is_streaming:
            return

        # Clear input
        self._input_field.model.set_value("")

        # Send message asynchronously
        asyncio.ensure_future(self._send_message(message))

    async def _send_message(self, message: str):
        """Send message and stream response.

        Args:
            message: User message to send
        """
        # Add user message to UI
        user_msg = MessageWidget("user", message)
        with self._message_container:
            user_msg.build()
        self.messages.append(user_msg)

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        # Scroll to bottom
        self._scroll_to_bottom()

        # Update status
        self._status_indicator.set_status("thinking")
        self._is_streaming = True
        self._send_button.enabled = False

        # Create assistant message widget
        self._current_assistant_message = MessageWidget("assistant", "")
        with self._message_container:
            self._current_assistant_message.build()
        self.messages.append(self._current_assistant_message)

        # Stream response with tool support
        try:
            full_response = ""
            self._tool_widgets.clear()

            async for event in self.client.stream_chat(
                message=message,
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens,
                conversation_history=self.conversation_history[:-1]  # Exclude current message
            ):
                event_type = event.get("type", "")

                if event.get("error") and event_type != "tool_result":
                    error_msg = event["error"]
                    carb.log_error(f"Chat error: {error_msg}")
                    self._current_assistant_message.set_content(f"Error: {error_msg}")
                    self._status_indicator.set_status("error", error_msg)
                    break

                if event_type == "text_delta":
                    # Text content from LLM
                    content = event.get("content", "")
                    if content:
                        full_response += content
                        self._current_assistant_message.append_content(content)
                        self._scroll_to_bottom()
                    self._status_indicator.set_status("thinking")

                elif event_type == "tool_call":
                    # Tool is being called
                    tool_name = event.get("tool", "unknown")
                    call_id = event.get("call_id", "")
                    params = event.get("params", {})

                    carb.log_info(f"Tool call: {tool_name} ({call_id})")
                    self._status_indicator.set_status("tool", f"Using {tool_name}...")

                    # Create tool call widget
                    tool_widget = ToolCallWidget(tool_name, call_id, params)
                    with self._message_container:
                        tool_widget.build()
                    self._tool_widgets[call_id] = tool_widget
                    self._scroll_to_bottom()

                elif event_type == "tool_result":
                    # Tool execution completed
                    call_id = event.get("call_id", "")
                    result = event.get("result", {})
                    success = result.get("success", False)

                    carb.log_info(f"Tool result: {call_id} success={success}")

                    # Update tool widget with result
                    if call_id in self._tool_widgets:
                        self._tool_widgets[call_id].set_result(result, success)
                        self._scroll_to_bottom()

                    self._status_indicator.set_status("thinking")

                elif event_type == "end":
                    # Streaming complete
                    self.conversation_history.append({"role": "assistant", "content": full_response})
                    self._status_indicator.set_status("ready")
                    break

                elif event_type == "error":
                    error_msg = event.get("error", "Unknown error")
                    carb.log_error(f"Stream error: {error_msg}")
                    self._status_indicator.set_status("error", error_msg)
                    break

                # Legacy support for old format
                elif event.get("done", False):
                    self.conversation_history.append({"role": "assistant", "content": full_response})
                    self._status_indicator.set_status("ready")
                    break

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            carb.log_error(error_msg)
            self._current_assistant_message.set_content(f"Error: {error_msg}")
            self._status_indicator.set_status("error", error_msg)

        finally:
            self._is_streaming = False
            self._send_button.enabled = True
            self._current_assistant_message = None
            self._tool_widgets.clear()

    def _scroll_to_bottom(self):
        """Scroll message container to bottom."""
        if self._scroll_frame:
            # Force UI update and scroll
            self._scroll_frame.scroll_y = self._scroll_frame.scroll_y_max

    def clear_chat(self):
        """Clear all messages and conversation history."""
        self.messages.clear()
        self.conversation_history.clear()

        # Rebuild message container
        if self._message_container:
            self._message_container.clear()

        self._status_indicator.set_status("ready")

    async def check_backend_health(self) -> bool:
        """Check if backend is available.

        Returns:
            True if backend is healthy, False otherwise
        """
        is_healthy = await self.client.health_check()

        if self._status_indicator:  # Defensive check
            if is_healthy:
                self._status_indicator.set_status("ready")
                carb.log_info("Backend connection successful")
            else:
                self._status_indicator.set_status("error", "Backend unavailable")
                carb.log_warn("Backend is not available")
        else:
            carb.log_warn("Status indicator not initialized yet")

        return is_healthy

    def destroy(self):
        """Clean up resources."""
        asyncio.ensure_future(self.client.close())
        super().destroy()
