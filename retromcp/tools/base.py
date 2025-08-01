"""Base class for MCP tools."""

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

try:
    from ..container import Container
except ImportError:
    from container import Container


class BaseTool(ABC):
    """Base class for all RetroMCP tools."""

    def __init__(self, container: Container) -> None:
        self.container = container
        self.config = container.config

    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return list of MCP tools provided by this module."""
        pass

    @abstractmethod
    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle a tool call for this module."""
        pass

    def format_error(self, message: str) -> List[TextContent]:
        """Format an error message."""
        return [TextContent(type="text", text=f"❌ {message}")]

    def format_success(self, message: str) -> List[TextContent]:
        """Format a success message."""
        return [TextContent(type="text", text=f"✅ {message}")]

    def format_warning(self, message: str) -> List[TextContent]:
        """Format a warning message."""
        return [TextContent(type="text", text=f"⚠️ {message}")]

    def format_info(self, message: str) -> List[TextContent]:
        """Format an info message."""
        return [TextContent(type="text", text=f"i {message}")]
