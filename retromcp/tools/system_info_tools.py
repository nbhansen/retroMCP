"""System information tools for retrieving system details."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class SystemInfoTools(BaseTool):
    """Tools for retrieving system information."""

    def get_tools(self) -> List[Tool]:
        """Return list of available system info tools."""
        return [
            Tool(
                name="get_system_info",
                description="Get comprehensive system information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["all", "hardware", "network", "storage", "processes", "services"],
                            "description": "Category of system information to retrieve",
                            "default": "all",
                        },
                    },
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle system info tool calls."""
        if name == "get_system_info":
            return await self._handle_system_info(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_system_info(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle system information retrieval."""
        try:
            category = arguments.get("category", "all")

            # Get the use case from container
            use_case = self.container.get_system_info_use_case
            system_info = use_case.execute()

            if category == "all":
                info_text = self._format_complete_system_info(system_info)
            elif category == "hardware":
                info_text = self._format_hardware_info(system_info)
            elif category == "network":
                info_text = self._format_network_info(system_info)
            elif category == "storage":
                info_text = self._format_storage_info(system_info)
            elif category == "processes":
                info_text = self._format_process_info(system_info)
            elif category == "services":
                info_text = self._format_service_info(system_info)
            else:
                return self.format_error(f"Unknown category: {category}")

            return self.format_success(info_text)

        except Exception as e:
            return self.format_error(f"System info error: {e!s}")

    def _format_complete_system_info(self, system_info) -> str:
        """Format complete system information."""
        return f"""System Information:

🖥️ Hardware:
- Hostname: {system_info.hostname}
- CPU Temperature: {system_info.cpu_temperature}°C
- Load Average: {system_info.load_average}
- Uptime: {system_info.uptime}

💾 Memory:
- Total: {system_info.memory_total / 1024 / 1024:.1f} MB
- Used: {system_info.memory_used / 1024 / 1024:.1f} MB
- Free: {system_info.memory_free / 1024 / 1024:.1f} MB

💽 Storage:
- Total: {system_info.disk_total / 1024 / 1024 / 1024:.1f} GB
- Used: {system_info.disk_used / 1024 / 1024 / 1024:.1f} GB
- Free: {system_info.disk_free / 1024 / 1024 / 1024:.1f} GB
"""

    def _format_hardware_info(self, system_info) -> str:
        """Format hardware information."""
        return f"""🖥️ Hardware Information:
- Hostname: {system_info.hostname}
- CPU Temperature: {system_info.cpu_temperature}°C
- Load Average: {system_info.load_average}
- Uptime: {system_info.uptime}
"""

    def _format_network_info(self, system_info) -> str:
        """Format network information."""
        return f"""🌐 Network Information:
- Hostname: {system_info.hostname}
- Network interfaces and details would be shown here
"""

    def _format_storage_info(self, system_info) -> str:
        """Format storage information."""
        return f"""💽 Storage Information:
- Total: {system_info.disk_total / 1024 / 1024 / 1024:.1f} GB
- Used: {system_info.disk_used / 1024 / 1024 / 1024:.1f} GB
- Free: {system_info.disk_free / 1024 / 1024 / 1024:.1f} GB
- Usage: {(system_info.disk_used / system_info.disk_total) * 100:.1f}%
"""

    def _format_process_info(self, system_info) -> str:
        """Format process information."""
        return f"""⚙️ Process Information:
- Load Average: {system_info.load_average}
- Memory Usage: {(system_info.memory_used / system_info.memory_total) * 100:.1f}%
- Process details would be shown here
"""

    def _format_service_info(self, system_info) -> str:
        """Format service information."""
        return f"""🔧 Service Information:
- System uptime: {system_info.uptime}
- Service status details would be shown here
"""
