"""Hardware monitoring tools for unified hardware management operations."""

import shlex
from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class HardwareMonitoringTools(BaseTool):
    """Unified hardware monitoring tools for all hardware management operations."""

    def get_tools(self) -> List[Tool]:
        """Return list of available hardware monitoring tools.

        Returns:
            List containing single manage_hardware tool.
        """
        return [
            Tool(
                name="manage_hardware",
                description="Unified hardware monitoring tool for temperature, fan, power, gpio, errors, and system overview",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component": {
                            "type": "string",
                            "enum": [
                                "temperature",
                                "fan",
                                "power",
                                "gpio",
                                "errors",
                                "all",
                            ],
                            "description": "Hardware component to manage",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform on the component",
                        },
                        # GPIO-specific parameters
                        "pin": {
                            "type": "integer",
                            "description": "GPIO pin number (0-40)",
                        },
                        # Temperature-specific parameters
                        "threshold": {
                            "type": "number",
                            "description": "Temperature threshold for monitoring",
                        },
                        # Fan-specific parameters
                        "speed": {
                            "type": "integer",
                            "description": "Fan speed percentage (0-100)",
                        },
                        # Error-specific parameters
                        "lines": {
                            "type": "integer",
                            "description": "Number of error lines to analyze",
                        },
                    },
                    "required": ["component", "action"],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for hardware monitoring operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_hardware":
                return await self._manage_hardware(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_hardware(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Route hardware management requests to appropriate handlers."""
        component = arguments.get("component")
        action = arguments.get("action")

        if not component:
            return self.format_error("Component is required")
        if not action:
            return self.format_error("Action is required")

        # Route to appropriate component handler
        if component == "temperature":
            return await self._handle_temperature(action, arguments)
        elif component == "fan":
            return await self._handle_fan(action, arguments)
        elif component == "power":
            return await self._handle_power(action, arguments)
        elif component == "gpio":
            return await self._handle_gpio(action, arguments)
        elif component == "errors":
            return await self._handle_errors(action, arguments)
        elif component == "all":
            return await self._handle_all(action, arguments)
        else:
            return self.format_error(f"Invalid component: {component}")

    async def _handle_temperature(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle temperature monitoring operations."""
        valid_actions = ["check", "monitor", "configure", "inspect"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_temperatures()
        elif action == "monitor":
            threshold = arguments.get("threshold", 75.0)
            return await self._monitor_temperatures(threshold)
        elif action == "configure":
            return await self._configure_temperature_settings(arguments)
        elif action == "inspect":
            return await self._inspect_temperature_details()
        else:
            return self.format_error(f"Temperature action '{action}' not implemented")

    async def _handle_fan(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle fan monitoring operations."""
        valid_actions = ["check", "monitor", "configure", "test"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_fan_status()
        elif action == "monitor":
            return await self._monitor_fan_control()
        elif action == "configure":
            speed = arguments.get("speed", 100)
            return await self._configure_fan_speed(speed)
        elif action == "test":
            return await self._test_fan_operation()
        else:
            return self.format_error(f"Fan action '{action}' not implemented")

    async def _handle_power(
        self,
        action: str,
        arguments: Dict[str, Any],  # noqa: ARG002
    ) -> List[TextContent]:
        """Handle power monitoring operations."""
        valid_actions = ["check", "monitor", "inspect"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_power_supply()
        elif action == "monitor":
            return await self._monitor_power_status()
        elif action == "inspect":
            return await self._inspect_power_details()
        else:
            return self.format_error(f"Power action '{action}' not implemented")

    async def _handle_gpio(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle GPIO monitoring operations."""
        valid_actions = ["check", "test", "configure"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_gpio_status()
        elif action == "test":
            pin = arguments.get("pin")
            if pin is None:
                return self.format_error("Pin number is required for GPIO test")
            if not isinstance(pin, int) or pin < 0 or pin > 40:
                return self.format_error("Invalid pin number. Must be between 0 and 40")
            return await self._test_gpio_pin(pin)
        elif action == "configure":
            return await self._configure_gpio_settings(arguments)
        else:
            return self.format_error(f"GPIO action '{action}' not implemented")

    async def _handle_errors(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle hardware error monitoring operations."""
        valid_actions = ["check", "inspect"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_hardware_errors()
        elif action == "inspect":
            lines = arguments.get("lines", 50)
            return await self._inspect_hardware_errors(lines)
        else:
            return self.format_error(f"Errors action '{action}' not implemented")

    async def _handle_all(
        self,
        action: str,
        arguments: Dict[str, Any],  # noqa: ARG002
    ) -> List[TextContent]:
        """Handle comprehensive hardware overview operations."""
        valid_actions = ["check", "inspect"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "check":
            return await self._check_all_hardware()
        elif action == "inspect":
            return await self._inspect_all_hardware()
        else:
            return self.format_error(f"All hardware action '{action}' not implemented")

    # Temperature monitoring methods

    async def _check_temperatures(self) -> List[TextContent]:
        """Check current CPU and GPU temperatures."""
        output = "🌡️ **Temperature Status**\n\n"

        try:
            # Get CPU temperature
            cpu_result = self.container.retropie_client.execute_command(
                "vcgencmd measure_temp"
            )
            if cpu_result.success and cpu_result.stdout:
                cpu_temp_str = cpu_result.stdout.strip()
                if "temp=" in cpu_temp_str:
                    cpu_temp = float(cpu_temp_str.split("=")[1].rstrip("'C"))
                    cpu_status = self._get_temperature_status(cpu_temp)
                    output += f"CPU: {cpu_status} {cpu_temp}°C\n"
                else:
                    output += "CPU: ❓ Unable to read temperature\n"
            else:
                output += "CPU: ❌ Failed to read temperature\n"

            # Get GPU temperature
            gpu_result = self.container.retropie_client.execute_command(
                "vcgencmd measure_temp gpu"
            )
            if gpu_result.success and gpu_result.stdout:
                gpu_temp_str = gpu_result.stdout.strip()
                if "temp=" in gpu_temp_str:
                    gpu_temp = float(gpu_temp_str.split("=")[1].rstrip("'C"))
                    gpu_status = self._get_temperature_status(gpu_temp)
                    output += f"GPU: {gpu_status} {gpu_temp}°C\n"
                else:
                    output += "GPU: ❓ Unable to read temperature\n"
            else:
                output += "GPU: ❌ Failed to read temperature\n"

            # Check throttling status
            throttle_result = self.container.retropie_client.execute_command(
                "vcgencmd get_throttled"
            )
            if throttle_result.success and throttle_result.stdout:
                throttle_value = throttle_result.stdout.strip()
                if "throttled=" in throttle_value:
                    throttle_hex = throttle_value.split("=")[1]
                    throttle_status = self._parse_throttling_status(throttle_hex)
                    output += f"\n{throttle_status}"

        except Exception as e:
            return self.format_error(f"Failed to check temperatures: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _monitor_temperatures(self, threshold: float) -> List[TextContent]:
        """Monitor temperatures with custom threshold."""
        # For now, just check current temperatures and compare to threshold
        temp_check = await self._check_temperatures()
        output = temp_check[0].text + f"\n\n**Monitor Threshold**: {threshold}°C"
        return [TextContent(type="text", text=output)]

    async def _configure_temperature_settings(
        self,
        arguments: Dict[str, Any],  # noqa: ARG002
    ) -> List[TextContent]:
        """Configure temperature monitoring settings."""
        return self.format_info("Temperature configuration not yet implemented")

    async def _inspect_temperature_details(self) -> List[TextContent]:
        """Inspect detailed temperature information."""
        return self.format_info("Temperature inspection not yet implemented")

    # Fan monitoring methods

    async def _check_fan_status(self) -> List[TextContent]:
        """Check fan control status."""
        output = "🌀 **Fan Control Status**\n\n"

        try:
            # Get current temperature for context
            temp_result = self.container.retropie_client.execute_command(
                "vcgencmd measure_temp"
            )
            if temp_result.success and temp_result.stdout:
                temp_str = temp_result.stdout.strip()
                if "temp=" in temp_str:
                    temp = float(temp_str.split("=")[1].rstrip("'C"))
                    output += f"Current Temperature: {temp}°C\n\n"

            # Check for thermal cooling devices
            cooling_result = self.container.retropie_client.execute_command(
                "ls -la /sys/class/thermal/cooling_device*/"
            )
            if cooling_result.success and cooling_result.stdout:
                output += "Cooling devices detected:\n"
                output += "```\n"
                output += cooling_result.stdout
                output += "```\n"
            else:
                output += "No active cooling devices detected\n"

        except Exception as e:
            return self.format_error(f"Failed to check fan status: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _monitor_fan_control(self) -> List[TextContent]:
        """Monitor fan control operation."""
        return self.format_info("Fan monitoring not yet implemented")

    async def _configure_fan_speed(self, speed: int) -> List[TextContent]:
        """Configure fan speed."""
        return self.format_info(
            f"Fan speed configuration to {speed}% not yet implemented"
        )

    async def _test_fan_operation(self) -> List[TextContent]:
        """Test fan operation."""
        return self.format_info("Fan operation testing not yet implemented")

    # Power monitoring methods

    async def _check_power_supply(self) -> List[TextContent]:
        """Check power supply status."""
        output = "⚡ **Power Supply Status**\n\n"

        try:
            # Check throttling status for power-related issues
            throttle_result = self.container.retropie_client.execute_command(
                "vcgencmd get_throttled"
            )
            if throttle_result.success and throttle_result.stdout:
                throttle_value = throttle_result.stdout.strip()
                if "throttled=" in throttle_value:
                    throttle_hex = throttle_value.split("=")[1]
                    throttle_int = int(throttle_hex, 16)

                    # Check for under-voltage flags
                    if throttle_int & 0x1:  # Under-voltage detected
                        output += "⚠️ **UNDER-VOLTAGE DETECTED**\n"
                    elif throttle_int & 0x10000:  # Under-voltage occurred
                        output += "🟡 **UNDER-VOLTAGE OCCURRED** (resolved)\n"
                    else:
                        output += "✅ **HEALTHY** - No power issues detected\n"

            # Check for voltage warnings in system logs
            voltage_result = self.container.retropie_client.execute_command(
                "dmesg | grep -i 'voltage' | tail -10"
            )
            if voltage_result.success and voltage_result.stdout.strip():
                output += "\n**Recent Voltage Warnings:**\n```\n"
                output += voltage_result.stdout
                output += "\n```"

        except Exception as e:
            return self.format_error(f"Failed to check power supply: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _monitor_power_status(self) -> List[TextContent]:
        """Monitor power supply status."""
        return self.format_info("Power monitoring not yet implemented")

    async def _inspect_power_details(self) -> List[TextContent]:
        """Inspect detailed power information."""
        return self.format_info("Power inspection not yet implemented")

    # GPIO monitoring methods

    async def _check_gpio_status(self) -> List[TextContent]:
        """Check GPIO pin status."""
        output = "🔌 **GPIO Pin Status**\n\n"

        try:
            # Get GPIO status using gpio readall command
            gpio_result = self.container.retropie_client.execute_command("gpio readall")
            if gpio_result.success and gpio_result.stdout:
                output += "```\n"
                output += gpio_result.stdout
                output += "\n```"
            else:
                output += "❌ Failed to read GPIO status\n"
                output += "Note: `gpio` command may not be available\n"

        except Exception as e:
            return self.format_error(f"Failed to check GPIO status: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _test_gpio_pin(self, pin: int) -> List[TextContent]:
        """Test specific GPIO pin."""
        output = f"🔌 **GPIO Pin {pin} Test**\n\n"

        try:
            # Read GPIO pin value
            quoted_pin = shlex.quote(str(pin))
            gpio_result = self.container.retropie_client.execute_command(
                f"gpio read {quoted_pin}"
            )
            if gpio_result.success and gpio_result.stdout:
                value = gpio_result.stdout.strip()
                state = "HIGH" if value == "1" else "LOW"
                output += f"Pin {pin} State: **{state}** ({value})\n"
            else:
                output += f"❌ Failed to read GPIO pin {pin}\n"

        except Exception as e:
            return self.format_error(f"Failed to test GPIO pin {pin}: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _configure_gpio_settings(
        self, _arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Configure GPIO settings."""
        return self.format_info("GPIO configuration not yet implemented")

    # Error monitoring methods

    async def _check_hardware_errors(self) -> List[TextContent]:
        """Check for hardware errors."""
        output = "🔍 **Hardware Error Analysis**\n\n"

        try:
            # Check dmesg for hardware-related errors
            dmesg_result = self.container.retropie_client.execute_command(
                "dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10"
            )

            # Check systemd journal for errors
            journal_result = self.container.retropie_client.execute_command(
                "journalctl -p err -n 10 --no-pager"
            )

            errors_found = False

            if dmesg_result.success and dmesg_result.stdout.strip():
                output += "**System Log Errors:**\n```\n"
                output += dmesg_result.stdout
                output += "\n```\n\n"
                errors_found = True

            if (
                journal_result.success
                and journal_result.stdout.strip()
                and "No entries" not in journal_result.stdout
            ):
                output += "**Journal Errors:**\n```\n"
                output += journal_result.stdout
                output += "\n```\n\n"
                errors_found = True

            if not errors_found:
                output += "✅ No hardware errors detected\n"

        except Exception as e:
            return self.format_error(f"Failed to check hardware errors: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _inspect_hardware_errors(self, lines: int) -> List[TextContent]:
        """Inspect hardware errors in detail."""
        return self.format_info(
            f"Hardware error inspection with {lines} lines not yet implemented"
        )

    # Comprehensive monitoring methods

    async def _check_all_hardware(self) -> List[TextContent]:
        """Check all hardware components."""
        output = "🖥️ **Hardware System Overview**\n\n"

        try:
            # Temperature check
            temp_result = await self._check_temperatures()
            output += "## Temperature\n" + temp_result[0].text + "\n\n"

            # Power check
            power_result = await self._check_power_supply()
            output += "## Power\n" + power_result[0].text + "\n\n"

            # Error check
            error_result = await self._check_hardware_errors()
            output += "## Errors\n" + error_result[0].text

        except Exception as e:
            return self.format_error(f"Failed to check all hardware: {e!s}")

        return [TextContent(type="text", text=output)]

    async def _inspect_all_hardware(self) -> List[TextContent]:
        """Inspect all hardware components in detail."""
        return self.format_info("Comprehensive hardware inspection not yet implemented")

    # Helper methods

    def _get_temperature_status(self, temp: float) -> str:
        """Get temperature status emoji based on temperature."""
        if temp < 60:
            return "✅ NORMAL"
        elif temp < 70:
            return "🟡 WARM"
        elif temp < 80:
            return "⚠️ HIGH"
        else:
            return "🔥 CRITICAL"

    def _parse_throttling_status(self, throttle_hex: str) -> str:
        """Parse throttling status from hex value."""
        try:
            throttle_int = int(throttle_hex, 16)
            status_parts = []

            # Current throttling flags
            if throttle_int & 0x1:
                status_parts.append("🔥 Under-voltage detected")
            if throttle_int & 0x2:
                status_parts.append("🌡️ ARM frequency capped")
            if throttle_int & 0x4:
                status_parts.append("⚠️ Currently throttled")
            if throttle_int & 0x8:
                status_parts.append("🔥 Soft temperature limit active")

            # Historical throttling flags
            if throttle_int & 0x10000:
                status_parts.append("🟡 Under-voltage occurred")
            if throttle_int & 0x20000:
                status_parts.append("🟡 ARM frequency capping occurred")
            if throttle_int & 0x40000:
                status_parts.append("🟡 Throttling occurred")
            if throttle_int & 0x80000:
                status_parts.append("🟡 Soft temperature limit occurred")

            if status_parts:
                return "**Throttling Status:**\n" + "\n".join(
                    f"- {part}" for part in status_parts
                )
            else:
                return "**Throttling Status:** ✅ No throttling detected"

        except ValueError:
            return f"**Throttling Status:** ❓ Unable to parse ({throttle_hex})"
