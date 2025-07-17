"""State management tools for RetroMCP."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import StateAction
from ..domain.models import StateManagementRequest
from ..domain.models import StateManagementResult
from .base import BaseTool


class StateTools(BaseTool):
    """Tools for system state management."""

    def get_tools(self) -> List[Tool]:
        """Return list of available state management tools.

        Returns:
            List of Tool objects for state management operations.
        """
        return [
            Tool(
                name="manage_state",
                description="Manage persistent system state by storing/retrieving structured data about the RetroPie configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "load",
                                "save",
                                "update",
                                "compare",
                                "export",
                                "import",
                                "diff",
                                "watch",
                            ],
                            "description": "Action to perform: load (retrieve cached state), save (scan and persist current state), update (modify specific field), compare (detect configuration drift), export (backup state to JSON), import (restore state from JSON), diff (compare with another state), watch (monitor specific field)",
                        },
                        "path": {
                            "type": "string",
                            "description": "Field path for update or watch actions (e.g., 'system.hostname')",
                        },
                        "value": {
                            "description": "New value for update action (any type)"
                        },
                        "force_scan": {
                            "type": "boolean",
                            "description": "Force full system scan for save action",
                            "default": False,
                        },
                        "state_data": {
                            "type": "string",
                            "description": "JSON state data for import action",
                        },
                        "other_state_data": {
                            "type": "string",
                            "description": "JSON state data to compare against for diff action",
                        },
                    },
                    "required": ["action"],
                    "additionalProperties": False,
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for state management operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_state":
                return await self._manage_state(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_state(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle state management operations."""
        action_str = arguments.get("action")
        path = arguments.get("path")  # Store path for later use

        if not action_str:
            return self.format_error("Action is required")

        # Validate action
        try:
            action = StateAction(action_str)
        except ValueError:
            return self.format_error(f"Invalid action: {action_str}")

        # Validate action-specific arguments
        if action == StateAction.UPDATE:
            value = arguments.get("value")

            if not path or value is None:
                return self.format_error(
                    "Path and value are required for update action"
                )
        elif action == StateAction.WATCH:
            if not path:
                return self.format_error("Path is required for watch action")
        elif action == StateAction.IMPORT:
            state_data = arguments.get("state_data")
            if not state_data:
                return self.format_error("state_data is required for import action")
        elif action == StateAction.DIFF:
            other_state_data = arguments.get("other_state_data")
            if not other_state_data:
                return self.format_error("other_state_data is required for diff action")

        # Build request
        request = StateManagementRequest(
            action=action,
            path=path,
            value=arguments.get("value"),
            force_scan=arguments.get("force_scan", False),
            state_data=arguments.get("state_data"),
            other_state_data=arguments.get("other_state_data"),
        )

        # Execute use case
        result = self.container.manage_state_use_case.execute(request)

        if result.success:
            return self._format_success_response(result, path)
        else:
            return self.format_error(result.message)

    def _format_success_response(
        self, result: StateManagementResult, path: Optional[str] = None
    ) -> List[TextContent]:
        """Format successful state management response."""
        response_text = f"✅ {result.message}\n\n"

        if result.action == StateAction.LOAD and result.state:
            # Format loaded state with enhanced v2.0 presentation
            state = result.state
            response_text += f"🔄 System State (Schema v{state.schema_version})\n"
            response_text += f"📅 Last Updated: {state.last_updated}\n"
            response_text += "━" * 80 + "\n\n"

            # Enhanced System Information Section
            response_text += "🖥️ System Information:\n"
            response_text += "━" * 40 + "\n"

            if "hostname" in state.system:
                response_text += f"  🏷️ Hostname: {state.system['hostname']}\n"

            if "cpu_temperature" in state.system:
                temp = state.system['cpu_temperature']
                temp_emoji = "🌡️" if temp < 60 else "🔥" if temp > 80 else "🌡️"
                response_text += f"  {temp_emoji} CPU Temperature: {temp}°C\n"

            # Enhanced memory information
            if "memory_total" in state.system:
                memory_total_gb = state.system["memory_total"] / (1024 * 1024 * 1024)
                memory_info = f"💾 Memory: {memory_total_gb:.1f}GB total"

                if "memory_used" in state.system and "memory_free" in state.system:
                    memory_used_gb = state.system["memory_used"] / (1024 * 1024 * 1024)
                    memory_free_gb = state.system["memory_free"] / (1024 * 1024 * 1024)
                    usage_percent = (state.system["memory_used"] / state.system["memory_total"]) * 100
                    memory_info += f" ({memory_used_gb:.1f}GB used, {memory_free_gb:.1f}GB free, {usage_percent:.1f}% used)"

                response_text += f"  {memory_info}\n"

            # Enhanced disk information
            if "disk_total" in state.system:
                disk_total_gb = state.system["disk_total"] / (1024 * 1024 * 1024)
                disk_info = f"💿 Storage: {disk_total_gb:.1f}GB total"

                if "disk_used" in state.system and "disk_free" in state.system:
                    disk_used_gb = state.system["disk_used"] / (1024 * 1024 * 1024)
                    disk_free_gb = state.system["disk_free"] / (1024 * 1024 * 1024)
                    usage_percent = (state.system["disk_used"] / state.system["disk_total"]) * 100
                    disk_info += f" ({disk_used_gb:.1f}GB used, {disk_free_gb:.1f}GB free, {usage_percent:.1f}% used)"

                response_text += f"  {disk_info}\n"

            # System performance
            if "load_average" in state.system:
                load_avg = state.system["load_average"]
                if isinstance(load_avg, list) and len(load_avg) >= 3:
                    response_text += f"  📊 Load Average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f} (1m, 5m, 15m)\n"

            if "uptime" in state.system:
                uptime_hours = state.system["uptime"] / 3600
                if uptime_hours < 24:
                    response_text += f"  ⏱️ Uptime: {uptime_hours:.1f} hours\n"
                else:
                    uptime_days = uptime_hours / 24
                    response_text += f"  ⏱️ Uptime: {uptime_days:.1f} days\n"

            # Enhanced Emulators Section
            response_text += "\n🎮 Emulation Systems:\n"
            response_text += "━" * 40 + "\n"
            installed = state.emulators.get("installed", [])
            preferred = state.emulators.get("preferred", {})

            if installed:
                response_text += f"  🎯 Installed Emulators: {len(installed)}\n"
                for emulator in installed:
                    preferred_systems = [k for k, v in preferred.items() if v == emulator]
                    if preferred_systems:
                        response_text += f"    • {emulator} (preferred for: {', '.join(preferred_systems)})\n"
                    else:
                        response_text += f"    • {emulator}\n"
            else:
                response_text += "  ❌ No emulators installed\n"

            # Enhanced Controllers Section
            response_text += "\n🎯 Input Controllers:\n"
            response_text += "━" * 40 + "\n"
            if state.controllers:
                response_text += f"  🎮 Detected Controllers: {len(state.controllers)}\n"
                for controller in state.controllers:
                    status_emoji = "✅" if controller.get("configured") else "❌"
                    status_text = "Configured" if controller.get("configured") else "Not configured"
                    controller_type = controller['type'].replace('_', ' ').title()
                    device_name = controller['device'].split('/')[-1] if '/' in controller['device'] else controller['device']

                    response_text += f"    {status_emoji} {controller_type}\n"
                    response_text += f"      📱 Device: {device_name}\n"
                    response_text += f"      ⚙️ Status: {status_text}\n"
            else:
                response_text += "  ❌ No controllers detected\n"

            # Enhanced ROMs Section
            response_text += "\n📁 ROM Collections:\n"
            response_text += "━" * 40 + "\n"
            rom_systems = state.roms.get("systems", [])
            rom_counts = state.roms.get("counts", {})

            if rom_systems:
                total_roms = sum(rom_counts.values())
                response_text += f"  🎲 Total ROMs: {total_roms} across {len(rom_systems)} systems\n"

                # Sort systems by ROM count for better presentation
                sorted_systems = sorted(rom_systems, key=lambda x: rom_counts.get(x, 0), reverse=True)

                for system in sorted_systems:
                    count = rom_counts.get(system, 0)
                    count_emoji = "🎯" if count > 10 else "📦" if count > 0 else "📭"
                    response_text += f"    {count_emoji} {system.upper()}: {count} ROMs\n"
            else:
                response_text += "  📭 No ROM directories found\n"

            # Enhanced Configuration & Issues Section
            if state.custom_configs or state.known_issues:
                response_text += "\n⚙️ System Configuration:\n"
                response_text += "━" * 40 + "\n"

                if state.custom_configs:
                    response_text += f"  🔧 Custom Configurations: {len(state.custom_configs)}\n"
                    for config in state.custom_configs:
                        response_text += f"    • {config}\n"

                if state.known_issues:
                    response_text += f"  ⚠️ Known Issues: {len(state.known_issues)}\n"
                    for issue in state.known_issues:
                        response_text += f"    • {issue}\n"

            # v2.0 Enhanced Fields Display
            if hasattr(state, 'hardware') and state.hardware:
                response_text += "\n🔧 Hardware Details:\n"
                response_text += "━" * 40 + "\n"
                hw = state.hardware
                response_text += f"  🖥️ Model: {hw.model}\n"
                response_text += f"  📟 Revision: {hw.revision}\n"
                if hw.storage:
                    response_text += f"  💾 Storage Devices: {len(hw.storage)}\n"
                    for storage in hw.storage:
                        response_text += f"    • {storage.device}: {storage.mount}\n"
                if hw.gpio_usage:
                    response_text += f"  🔌 GPIO Usage: {len(hw.gpio_usage)} pins\n"
                response_text += f"  🌪️ Cooling Active: {'Yes' if hw.cooling_active else 'No'}\n"

            if hasattr(state, 'network') and state.network:
                response_text += "\n🌐 Network Interfaces:\n"
                response_text += "━" * 40 + "\n"
                for interface in state.network:
                    status_emoji = "🟢" if interface.status.value == "up" else "🔴"
                    response_text += f"  {status_emoji} {interface.name} ({interface.ip})\n"
                    response_text += f"    🚀 Speed: {interface.speed}\n"
                    if interface.ssid:
                        signal_bars = "📶" if (interface.signal_strength or 0) > 50 else "📵"
                        response_text += f"    📡 WiFi: {interface.ssid} {signal_bars}\n"

            if hasattr(state, 'software') and state.software:
                response_text += "\n💿 Software Environment:\n"
                response_text += "━" * 40 + "\n"
                sw = state.software
                response_text += f"  🐧 OS: {sw.os_name} {sw.os_version}\n"
                response_text += f"  ⚙️ Kernel: {sw.kernel}\n"
                response_text += f"  🐍 Python: {sw.python_version}\n"
                docker_emoji = "🟢" if sw.docker_status.value == "running" else "🔴"
                response_text += f"  🐳 Docker: {sw.docker_version} {docker_emoji}\n"
                response_text += f"  🎮 RetroPie: {sw.retropie_version}\n"

        elif result.action == StateAction.EXPORT and result.exported_data:
            # Format export results
            response_text += "📤 State exported successfully!\n\n"
            response_text += "📄 Exported JSON Data:\n"
            response_text += "```json\n"
            response_text += result.exported_data
            response_text += "\n```\n"

        elif result.action == StateAction.IMPORT:
            # Format import results
            response_text += "📥 State imported successfully!\n"
            response_text += (
                "The system state has been restored from the provided backup.\n"
            )

        elif result.action == StateAction.WATCH and result.watch_value is not None:
            # Format watch results
            response_text += f"👁️ Watching field: {path or 'unknown'}\n"
            response_text += f"📊 Current value: {result.watch_value}\n"
            response_text += "Monitor will track changes to this field.\n"

        elif result.action in [StateAction.DIFF, StateAction.COMPARE] and result.diff:
            # Format comparison results
            diff = result.diff
            has_changes = bool(
                diff.get("added") or diff.get("changed") or diff.get("removed")
            )

            if not has_changes:
                response_text += (
                    "🎉 No differences found - system state is up to date!\n"
                )
            else:
                response_text += "🔍 Configuration drift detected:\n\n"

                # Added fields
                if diff.get("added"):
                    response_text += "+ Added fields:\n"
                    for path, value in diff["added"].items():
                        response_text += f"  • {path}: {value}\n"
                    response_text += "\n"

                # Changed fields
                if diff.get("changed"):
                    response_text += "🔄 Changed fields:\n"
                    for path, change in diff["changed"].items():
                        response_text += (
                            f"  • {path}: {change['old']} → {change['new']}\n"
                        )
                    response_text += "\n"

                # Removed fields
                if diff.get("removed"):
                    response_text += "- Removed fields:\n"
                    for path, value in diff["removed"].items():
                        response_text += f"  • {path}: {value}\n"
                    response_text += "\n"

        return [TextContent(type="text", text=response_text)]
