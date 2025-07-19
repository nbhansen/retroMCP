"""System management tools - consolidated focused tools."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool
from .command_execution_tools import CommandExecutionTools
from .connection_management_tools import ConnectionManagementTools
from .file_management_tools import FileManagementTools
from .package_management_tools import PackageManagementTools
from .service_management_tools import ServiceManagementTools
from .system_info_tools import SystemInfoTools
from .system_update_tools import SystemUpdateTools


class SystemManagementTools(BaseTool):
    """Consolidated system management tools using focused sub-tools."""

    def __init__(self, container) -> None:
        """Initialize with container and create sub-tools."""
        super().__init__(container)

        # Create focused sub-tools
        self.service_tools = ServiceManagementTools(container)
        self.package_tools = PackageManagementTools(container)
        self.file_tools = FileManagementTools(container)
        self.command_tools = CommandExecutionTools(container)
        self.connection_tools = ConnectionManagementTools(container)
        self.info_tools = SystemInfoTools(container)
        self.update_tools = SystemUpdateTools(container)

    def get_tools(self) -> List[Tool]:
        """Return list of all available system management tools."""
        tools = []

        # Collect tools from all sub-tools
        tools.extend(self.service_tools.get_tools())
        tools.extend(self.package_tools.get_tools())
        tools.extend(self.file_tools.get_tools())
        tools.extend(self.command_tools.get_tools())
        tools.extend(self.connection_tools.get_tools())
        tools.extend(self.info_tools.get_tools())
        tools.extend(self.update_tools.get_tools())

        return tools

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Route tool calls to appropriate sub-tools."""
        # Route to appropriate sub-tool based on tool name
        if name == "manage_service":
            return await self.service_tools.handle_tool_call(name, arguments)
        elif name == "manage_package":
            return await self.package_tools.handle_tool_call(name, arguments)
        elif name == "manage_file":
            return await self.file_tools.handle_tool_call(name, arguments)
        elif name == "execute_command":
            return await self.command_tools.handle_tool_call(name, arguments)
        elif name == "manage_connection":
            return await self.connection_tools.handle_tool_call(name, arguments)
        elif name == "get_system_info":
            return await self.info_tools.handle_tool_call(name, arguments)
        elif name == "update_system":
            return await self.update_tools.handle_tool_call(name, arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")
