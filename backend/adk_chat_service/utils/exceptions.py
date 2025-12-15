"""Custom exceptions for ADK Chat Service."""


class BackendError(Exception):
    """Base exception for all backend errors."""

    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class ADKClientError(BackendError):
    """Exception raised for errors in the ADK client."""

    pass


class ConfigurationError(BackendError):
    """Exception raised for configuration errors."""

    pass


class StreamingError(BackendError):
    """Exception raised for streaming-related errors."""

    pass


class ToolRegistrationError(BackendError):
    """Exception raised for tool registration errors (Phase 2 - MCP)."""

    pass
