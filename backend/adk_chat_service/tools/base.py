"""Base tool interface for MCP integration (Phase 2)."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """
    Abstract base class for MCP tools.

    Tools provide additional capabilities to the LLM through function calling.
    Each tool must implement the execute method and define its schema.
    """

    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        """
        Initialize a tool.

        Args:
            name: Tool name (unique identifier)
            description: Human-readable description of what the tool does
            parameters: JSON Schema defining tool parameters
        """
        self.name = name
        self.description = description
        self.parameters = parameters

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters matching the JSON Schema

        Returns:
            Any: Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        pass

    def to_mcp_schema(self) -> Dict[str, Any]:
        """
        Convert tool to MCP schema format.

        Returns:
            Dict: Tool schema in MCP format
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters
        }

    def to_genai_function_declaration(self) -> Dict[str, Any]:
        """
        Convert tool to Google GenAI function declaration format.

        Returns:
            Dict: Tool schema in GenAI format
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}'>"
