"""Message widget for displaying chat messages."""

import omni.ui as ui
from typing import Literal


class MessageWidget:
    """Widget for displaying a single chat message with streaming support."""

    def __init__(
        self,
        message_type: Literal["user", "assistant"],
        initial_content: str = ""
    ):
        """Initialize message widget.

        Args:
            message_type: Either "user" or "assistant"
            initial_content: Initial message content
        """
        self.message_type = message_type
        self._content = initial_content
        self._label: ui.Label = None

        # Style configuration
        if message_type == "user":
            self.bg_color = ui.color(0.2, 0.4, 0.8, 0.3)  # Blue tint
            self.alignment = ui.Alignment.RIGHT
            self.h_alignment = ui.Alignment.RIGHT_CENTER
        else:
            self.bg_color = ui.color(0.3, 0.3, 0.3, 0.3)  # Gray tint
            self.alignment = ui.Alignment.LEFT
            self.h_alignment = ui.Alignment.LEFT_CENTER

    def build(self) -> ui.Frame:
        """Build the message widget UI.

        Returns:
            Frame containing the message
        """
        frame = ui.Frame(height=0)
        with frame:
            with ui.HStack(spacing=5, height=0):
                if self.message_type == "user":
                    ui.Spacer(width=ui.Percent(20))

                with ui.ZStack(height=0):
                    # Background rectangle
                    ui.Rectangle(
                        style={
                            "background_color": self.bg_color,
                            "border_radius": 8,
                            "border_width": 1,
                            "border_color": ui.color(0.4, 0.4, 0.4, 0.5)
                        }
                    )

                    # Message content
                    with ui.VStack(spacing=0, height=0):
                        ui.Spacer(height=6)
                        with ui.HStack(height=0):
                            ui.Spacer(width=12)
                            self._label = ui.Label(
                                self._content,
                                word_wrap=True,
                                alignment=self.h_alignment,
                                style={
                                    "font_size": 16,
                                    "color": ui.color(0.9, 0.9, 0.9, 1.0)
                                }
                            )
                            ui.Spacer(width=12)
                        ui.Spacer(height=6)

                if self.message_type == "assistant":
                    ui.Spacer(width=ui.Percent(20))

        return frame

    def append_content(self, content: str):
        """Append content to the message (for streaming).

        Args:
            content: Text to append
        """
        self._content += content
        if self._label:
            self._label.text = self._content

    def set_content(self, content: str):
        """Replace entire message content.

        Args:
            content: New message content
        """
        self._content = content
        if self._label:
            self._label.text = self._content

    @property
    def content(self) -> str:
        """Get current message content."""
        return self._content


class StatusIndicator:
    """Widget for displaying connection and processing status."""

    def __init__(self):
        """Initialize status indicator."""
        self._status_label: ui.Label = None
        self._status_circle: ui.Circle = None
        self._current_color = ui.color(0.5, 0.5, 0.5, 1.0)

    def build(self) -> ui.Frame:
        """Build the status indicator UI.

        Returns:
            Frame containing the status indicator
        """
        frame = ui.Frame(height=ui.Pixel(20))
        with frame:
            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                self._status_circle = ui.Circle(
                    radius=5,
                    style={"background_color": self._current_color}
                )
                self._status_label = ui.Label(
                    "Ready",
                    style={"font_size": 16, "color": ui.color(0.8, 0.8, 0.8, 1.0)}
                )
                ui.Spacer()

        return frame

    def set_status(self, status: Literal["ready", "thinking", "error"], message: str = None):
        """Update status indicator.

        Args:
            status: Status type
            message: Optional custom status message
        """
        if status == "ready":
            new_color = ui.color(0.3, 0.8, 0.3, 1.0)  # Green
            default_msg = "Ready"
        elif status == "thinking":
            new_color = ui.color(0.8, 0.6, 0.2, 1.0)  # Orange
            default_msg = "Thinking..."
        else:  # error
            new_color = ui.color(0.8, 0.2, 0.2, 1.0)  # Red
            default_msg = "Error"

        self._current_color = new_color
        if self._status_circle:
            self._status_circle.set_style({"background_color": new_color})

        if self._status_label:
            self._status_label.text = message if message else default_msg
