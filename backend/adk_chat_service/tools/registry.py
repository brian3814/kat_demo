"""Tool registry for managing MCP tools (Phase 2)."""

from typing import Any, Dict, List, Optional

from .base import BaseTool
from ..utils.exceptions import ToolRegistrationError
from ..utils.logger import get_logger

logger = get_logger()


class ToolRegistry:
    """
    Registry for managing MCP tools.

    Provides plugin architecture for tool discovery, registration,
    and execution. Tools can be registered dynamically and integrated
    with the ADK client for function calling.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")

    def register(self, tool: BaseTool) -> None:
        """
        Register a new tool.

        Args:
            tool: Tool instance to register

        Raises:
            ToolRegistrationError: If tool name already registered
        """
        if tool.name in self._tools:
            raise ToolRegistrationError(
                message=f"Tool '{tool.name}' already registered",
                detail="Tool names must be unique"
            )

        self._tools[tool.name] = tool
        logger.info("Tool registered", tool_name=tool.name)

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of tool to unregister

        Raises:
            ToolRegistrationError: If tool not found
        """
        if tool_name not in self._tools:
            raise ToolRegistrationError(
                message=f"Tool '{tool_name}' not found",
                detail="Cannot unregister non-existent tool"
            )

        del self._tools[tool_name]
        logger.info("Tool unregistered", tool_name=tool_name)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retrieve tool by name.

        Args:
            name: Tool name

        Returns:
            BaseTool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_mcp_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tools in MCP schema format.

        Returns:
            List of tool schemas in MCP format
        """
        return [tool.to_mcp_schema() for tool in self._tools.values()]

    def get_genai_function_declarations(self) -> List[Dict[str, Any]]:
        """
        Get all tools in Google GenAI function declaration format.

        Returns:
            List of tool schemas in GenAI format
        """
        return [tool.to_genai_function_declaration() for tool in self._tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            ToolRegistrationError: If tool not found
            Exception: If tool execution fails
        """
        tool = self.get_tool(name)
        if not tool:
            raise ToolRegistrationError(
                message=f"Tool '{name}' not found",
                detail="Tool must be registered before execution"
            )

        logger.info("Executing tool", tool_name=name, parameters=kwargs)

        try:
            result = await tool.execute(**kwargs)
            logger.info("Tool execution completed", tool_name=name)
            return result
        except Exception as e:
            logger.error("Tool execution failed", tool_name=name, error=str(e))
            raise

    def discover_tools(self, plugin_path: str) -> int:
        """
        Discover and load tools from a plugin directory.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Number of tools discovered and loaded

        Note:
            This is a placeholder for Phase 2 implementation.
            Implement dynamic plugin loading based on your requirements.
        """
        logger.warning("Tool discovery not yet implemented (Phase 2)")
        # TODO: Implement plugin discovery
        return 0

    def clear(self) -> None:
        """Clear all registered tools."""
        count = len(self._tools)
        self._tools.clear()
        logger.info("Tool registry cleared", tools_removed=count)

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
