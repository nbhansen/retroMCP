"""Hardware monitoring and debugging tools for Raspberry Pi."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class HardwareTools(BaseTool):
    """Tools for hardware monitoring and debugging."""

    def get_tools(self) -> List[Tool]:
        """Return list of available hardware monitoring tools.

        Returns:
            List of Tool objects for hardware operations.
        """
        return [
            Tool(
                name="check_temperatures",
                description="Monitor CPU/GPU temperatures and thermal status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_history": {
                            "type": "boolean",
                            "description": "Include recent temperature history",
                            "default": False,
                        },
                        "check_throttling": {
                            "type": "boolean",
                            "description": "Check for thermal throttling events",
                            "default": True,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="monitor_fan_control",
                description="Check fan speed, control status, and cooling system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["status", "test", "configure"],
                            "description": "Fan monitoring action",
                            "default": "status",
                        },
                        "target_speed": {
                            "type": "integer",
                            "description": "Target fan speed percentage (for test action)",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="check_power_supply",
                description="Monitor power supply health and voltage levels",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Include detailed power analysis",
                            "default": False,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="inspect_hardware_errors",
                description="Check system logs for hardware-related errors",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "integer",
                            "description": "Hours of logs to analyze",
                            "default": 24,
                            "minimum": 1,
                            "maximum": 168,
                        },
                        "error_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "thermal",
                                    "power",
                                    "gpio",
                                    "usb",
                                    "memory",
                                    "all",
                                ],
                            },
                            "description": "Types of hardware errors to check",
                            "default": ["all"],
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="check_gpio_status",
                description="Monitor GPIO pin states and connected hardware",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pins": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Specific GPIO pins to check (optional)",
                        },
                        "show_all": {
                            "type": "boolean",
                            "description": "Show all GPIO pins status",
                            "default": False,
                        },
                    },
                    "required": [],
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
            if name == "check_temperatures":
                return await self._check_temperatures(arguments)
            elif name == "monitor_fan_control":
                return await self._monitor_fan_control(arguments)
            elif name == "check_power_supply":
                return await self._check_power_supply(arguments)
            elif name == "inspect_hardware_errors":
                return await self._inspect_hardware_errors(arguments)
            elif name == "check_gpio_status":
                return await self._check_gpio_status(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _check_temperatures(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Monitor system temperatures and thermal status."""
        include_history = arguments.get("include_history", False)
        check_throttling = arguments.get("check_throttling", True)

        output = "🌡️ **Temperature Monitoring**\n\n"

        # Get current CPU temperature
        exit_code, cpu_temp_raw, _ = self.ssh.execute_command("vcgencmd measure_temp")

        if exit_code == 0 and cpu_temp_raw:
            # Extract temperature value
            import re

            temp_match = re.search(r"temp=([0-9.]+)'C", cpu_temp_raw)
            if temp_match:
                cpu_temp = float(temp_match.group(1))
                output += f"**CPU Temperature:** {cpu_temp:.1f}°C"

                # Add warning levels
                if cpu_temp > 80:
                    output += " 🔥 **CRITICAL - OVERHEATING!**"
                elif cpu_temp > 70:
                    output += " ⚠️ **HIGH**"
                elif cpu_temp > 60:
                    output += " 🟡 **WARM**"
                else:
                    output += " ✅ **NORMAL**"

                output += "\n\n"
        else:
            output += "❌ Could not read CPU temperature\n\n"

        # Check thermal throttling status
        if check_throttling:
            exit_code, throttle_raw, _ = self.ssh.execute_command(
                "vcgencmd get_throttled"
            )

            if exit_code == 0 and throttle_raw:
                throttle_hex = (
                    throttle_raw.strip().split("=")[1] if "=" in throttle_raw else "0x0"
                )
                throttle_int = int(throttle_hex, 16)

                output += "**Thermal Status:**\n"

                # Decode throttling bits
                status_flags = []
                if throttle_int & 0x1:
                    status_flags.append("🔥 Under-voltage detected")
                if throttle_int & 0x2:
                    status_flags.append("🌡️ ARM frequency capped")
                if throttle_int & 0x4:
                    status_flags.append("⚡ Currently throttled")
                if throttle_int & 0x8:
                    status_flags.append("🌡️ Soft temperature limit active")
                if throttle_int & 0x10000:
                    status_flags.append("⚠️ Under-voltage has occurred")
                if throttle_int & 0x20000:
                    status_flags.append("⚠️ ARM frequency capping has occurred")
                if throttle_int & 0x40000:
                    status_flags.append("⚠️ Throttling has occurred")
                if throttle_int & 0x80000:
                    status_flags.append("⚠️ Soft temperature limit has occurred")

                if status_flags:
                    output += "\n".join(f"- {flag}" for flag in status_flags)
                else:
                    output += "✅ No thermal issues detected"

                output += "\n\n"

        # Check GPU temperature if available
        exit_code, gpu_temp_raw, _ = self.ssh.execute_command(
            "vcgencmd measure_temp gpu 2>/dev/null"
        )

        if exit_code == 0 and gpu_temp_raw:
            import re

            temp_match = re.search(r"temp=([0-9.]+)'C", gpu_temp_raw)
            if temp_match:
                gpu_temp = float(temp_match.group(1))
                output += f"**GPU Temperature:** {gpu_temp:.1f}°C\n\n"

        # Get temperature history if requested
        if include_history:
            output += "**Recent Temperature History:**\n"
            # Simple monitoring for 10 seconds
            exit_code, _, _ = self.ssh.execute_command(
                'for i in {1..5}; do echo "$(date): $(vcgencmd measure_temp)"; sleep 2; done'
            )
            output += "Temperature logged over 10 seconds\n\n"

        # Check cooling configuration
        output += "**Cooling Configuration:**\n"

        # Check if fan service is running
        exit_code, fan_service, _ = self.ssh.execute_command(
            "systemctl is-active pigpiod 2>/dev/null || echo 'not-running'"
        )

        if "active" in fan_service:
            output += "✅ GPIO daemon (pigpiod) is running\n"
        else:
            output += "⚠️ GPIO daemon not running (may affect fan control)\n"

        # Check for fan control scripts
        exit_code, fan_scripts, _ = self.ssh.execute_command(
            "ls /usr/local/bin/*fan* /home/*/fan* 2>/dev/null || echo 'No fan scripts found'"
        )

        if "No fan scripts found" not in fan_scripts:
            output += f"🌀 Fan control scripts found:\n{fan_scripts}\n"
        else:
            output += "ⓘ No fan control scripts detected\n"

        return [TextContent(type="text", text=output)]

    async def _monitor_fan_control(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Monitor fan control system and cooling."""
        action = arguments.get("action", "status")
        target_speed = arguments.get("target_speed")

        output = "🌀 **Fan Control Monitoring**\n\n"

        if action == "status":
            # Check GPIO daemon
            exit_code, gpio_status, _ = self.ssh.execute_command(
                "systemctl status pigpiod --no-pager -l 2>/dev/null"
            )

            output += "**GPIO Daemon Status:**\n"
            if exit_code == 0:
                output += "✅ pigpiod service is running\n\n"
            else:
                output += "❌ pigpiod service not running\n"
                output += "💡 Try: `sudo systemctl start pigpiod`\n\n"

            # Check for common fan GPIO pins
            common_fan_pins = [14, 15, 18]  # Common PWM pins
            output += "**Fan GPIO Pin Status:**\n"

            for pin in common_fan_pins:
                exit_code, pin_mode, _ = self.ssh.execute_command(
                    f"gpio -g mode {pin} 2>/dev/null && gpio -g read {pin} 2>/dev/null"
                )
                if exit_code == 0:
                    output += f"- GPIO {pin}: {pin_mode.strip()}\n"

            # Check for fan control processes
            exit_code, fan_processes, _ = self.ssh.execute_command(
                "ps aux | grep -i fan | grep -v grep"
            )

            output += "\n**Fan Control Processes:**\n"
            if exit_code == 0 and fan_processes.strip():
                output += f"{fan_processes}\n"
            else:
                output += "No fan control processes found\n"

            # Check device tree for PWM
            exit_code, pwm_status, _ = self.ssh.execute_command(
                "ls -la /sys/class/pwm/ 2>/dev/null"
            )

            if exit_code == 0:
                output += f"\n**PWM Interfaces:**\n{pwm_status}\n"

        elif action == "test" and target_speed is not None:
            output += f"**Testing Fan at {target_speed}% Speed**\n\n"

            # Try to control fan via GPIO (assuming GPIO 14)
            exit_code, _, stderr = self.ssh.execute_command(
                f"gpio -g mode 14 pwm && gpio -g pwm 14 {int(target_speed * 10.23)}"
            )

            if exit_code == 0:
                output += f"✅ Fan speed set to {target_speed}%\n"
                output += "🔍 Check if you can hear/feel the fan change\n"
            else:
                output += f"❌ Failed to control fan: {stderr}\n"
                output += "💡 Make sure GPIO tools are installed: `sudo apt install wiringpi`\n"

        elif action == "configure":
            output += "**Fan Configuration Guide**\n\n"
            output += "To set up automatic fan control:\n\n"
            output += "1. **Enable GPIO daemon:**\n"
            output += "   `sudo systemctl enable pigpiod`\n"
            output += "   `sudo systemctl start pigpiod`\n\n"
            output += "2. **Install fan control script:**\n"
            output += "   Create `/usr/local/bin/fan-control.py`\n\n"
            output += "3. **Common GPIO pins for fans:**\n"
            output += "   - GPIO 14 (PWM)\n"
            output += "   - GPIO 18 (PWM)\n"
            output += "   - GPIO 15 (Digital)\n\n"
            output += "4. **Add to crontab:**\n"
            output += "   `@reboot /usr/local/bin/fan-control.py &`\n"

        return [TextContent(type="text", text=output)]

    async def _check_power_supply(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Monitor power supply health and voltage levels."""
        detailed = arguments.get("detailed", False)

        output = "⚡ **Power Supply Monitoring**\n\n"

        # Check for under-voltage warnings
        exit_code, throttle_raw, _ = self.ssh.execute_command("vcgencmd get_throttled")

        if exit_code == 0:
            throttle_hex = (
                throttle_raw.strip().split("=")[1] if "=" in throttle_raw else "0x0"
            )
            throttle_int = int(throttle_hex, 16)

            output += "**Power Status:**\n"

            # Check current and historical under-voltage
            if throttle_int & 0x1:
                output += "🔴 **CURRENT UNDER-VOLTAGE DETECTED!**\n"
            elif throttle_int & 0x10000:
                output += "🟡 **Under-voltage occurred previously**\n"
            else:
                output += "✅ **No under-voltage issues**\n"

            output += "\n"

        # Get system voltage if available
        exit_code, core_volts, _ = self.ssh.execute_command(
            "vcgencmd measure_volts core"
        )

        if exit_code == 0 and core_volts:
            output += f"**Core Voltage:** {core_volts.strip()}\n"

        # Check power consumption estimate
        exit_code, arm_freq, _ = self.ssh.execute_command("vcgencmd measure_clock arm")

        if exit_code == 0 and arm_freq:
            freq_hz = arm_freq.strip().split("=")[1] if "=" in arm_freq else "0"
            freq_mhz = int(freq_hz) // 1000000 if freq_hz.isdigit() else 0
            output += f"**ARM Frequency:** {freq_mhz} MHz\n"

        if detailed:
            output += "\n**Detailed Power Analysis:**\n"

            # Check all voltage rails
            voltage_rails = ["core", "sdram_c", "sdram_i", "sdram_p"]
            for rail in voltage_rails:
                exit_code, volts, _ = self.ssh.execute_command(
                    f"vcgencmd measure_volts {rail} 2>/dev/null"
                )
                if exit_code == 0 and volts:
                    output += f"- {rail}: {volts.strip()}\n"

            # Check power supply recommendations
            output += "\n**Power Supply Recommendations:**\n"

            # Detect Pi model
            exit_code, pi_model, _ = self.ssh.execute_command(
                "cat /proc/device-tree/model 2>/dev/null"
            )

            if "Pi 4" in pi_model:
                output += "- Raspberry Pi 4: Minimum 3A (15W) USB-C supply\n"
                output += "- For heavy loads: 5A (25W) recommended\n"
            elif "Pi 3" in pi_model:
                output += "- Raspberry Pi 3: Minimum 2.5A (12.5W) micro-USB supply\n"

            # Check USB devices that might draw power
            exit_code, usb_devices, _ = self.ssh.execute_command("lsusb | wc -l")

            if exit_code == 0:
                device_count = int(usb_devices.strip()) - 1  # Subtract the hub
                output += f"- USB devices connected: {device_count}\n"
                if device_count > 2:
                    output += "  ⚠️ Multiple USB devices may require powered hub\n"

        # Power optimization tips
        output += "\n**Power Optimization Tips:**\n"
        output += "- Use quality power supply with thick, short cables\n"
        output += "- Avoid USB devices that draw excessive power\n"
        output += "- Consider powered USB hub for multiple devices\n"
        output += "- Monitor under-voltage warnings in logs\n"

        return [TextContent(type="text", text=output)]

    async def _inspect_hardware_errors(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Check system logs for hardware-related errors."""
        hours = arguments.get("hours", 24)
        error_types = arguments.get("error_types", ["all"])

        output = f"🔍 **Hardware Error Analysis (Last {hours} hours)**\n\n"

        # Build search patterns based on error types
        search_patterns = []

        if "all" in error_types or "thermal" in error_types:
            search_patterns.extend(
                ["temperature", "thermal", "throttled", "overheating"]
            )

        if "all" in error_types or "power" in error_types:
            search_patterns.extend(["under-voltage", "power", "voltage"])

        if "all" in error_types or "gpio" in error_types:
            search_patterns.extend(["gpio", "pin", "pwm"])

        if "all" in error_types or "usb" in error_types:
            search_patterns.extend(["usb", "device disconnect", "hub"])

        if "all" in error_types or "memory" in error_types:
            search_patterns.extend(["memory", "segfault", "oom", "killed"])

        # Check kernel messages
        output += "**Kernel Messages (dmesg):**\n"

        pattern_str = "|".join(search_patterns)
        exit_code, dmesg_errors, _ = self.ssh.execute_command(
            f"dmesg -T | grep -i -E '{pattern_str}' | tail -20"
        )

        if exit_code == 0 and dmesg_errors.strip():
            output += f"```\n{dmesg_errors}\n```\n\n"
        else:
            output += "✅ No recent hardware errors in kernel messages\n\n"

        # Check system logs
        output += "**System Logs:**\n"

        # Use journalctl to get logs from the specified time period
        exit_code, journal_errors, _ = self.ssh.execute_command(
            f"journalctl --since '{hours} hours ago' | grep -i -E '{pattern_str}' | tail -10"
        )

        if exit_code == 0 and journal_errors.strip():
            output += f"```\n{journal_errors}\n```\n\n"
        else:
            output += "✅ No hardware-related errors in system logs\n\n"

        # Check for specific hardware issues
        output += "**Specific Hardware Checks:**\n"

        # Memory errors
        exit_code, mem_errors, _ = self.ssh.execute_command(
            "grep -i 'memory error\\|segfault\\|killed process' /var/log/kern.log /var/log/syslog 2>/dev/null | tail -5"
        )

        if exit_code == 0 and mem_errors.strip():
            output += "⚠️ **Memory Issues Found:**\n"
            output += f"```\n{mem_errors}\n```\n"
        else:
            output += "✅ No memory errors detected\n"

        # USB issues
        exit_code, usb_errors, _ = self.ssh.execute_command(
            "grep -i 'usb.*disconnect\\|device not accepting\\|hub' /var/log/kern.log 2>/dev/null | tail -5"
        )

        if exit_code == 0 and usb_errors.strip():
            output += "⚠️ **USB Issues Found:**\n"
            output += f"```\n{usb_errors}\n```\n"
        else:
            output += "✅ No USB issues detected\n"

        # Temperature warnings
        exit_code, temp_warnings, _ = self.ssh.execute_command(
            "grep -i 'temperature\\|thermal\\|throttled' /var/log/kern.log 2>/dev/null | tail -5"
        )

        if exit_code == 0 and temp_warnings.strip():
            output += "🌡️ **Temperature Warnings:**\n"
            output += f"```\n{temp_warnings}\n```\n"
        else:
            output += "✅ No temperature warnings\n"

        # Recommendations
        output += "\n**Troubleshooting Recommendations:**\n"
        output += "- For thermal issues: Check cooling, clean heatsink, verify fan operation\n"
        output += "- For power issues: Use quality power supply, check cables\n"
        output += "- For USB issues: Try different ports, check power consumption\n"
        output += (
            "- For memory issues: Test with memtester, check for corrupted SD card\n"
        )

        return [TextContent(type="text", text=output)]

    async def _check_gpio_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Monitor GPIO pin states and connected hardware."""
        pins = arguments.get("pins", [])
        show_all = arguments.get("show_all", False)

        output = "📟 **GPIO Status Monitoring**\n\n"

        # Check if GPIO tools are available
        exit_code, gpio_check, _ = self.ssh.execute_command(
            "command -v gpio >/dev/null 2>&1 && echo 'available' || echo 'missing'"
        )

        if "missing" in gpio_check:
            output += "❌ **GPIO tools not installed**\n"
            output += "Install with: `sudo apt install wiringpi`\n\n"
            return [TextContent(type="text", text=output)]

        if pins:
            # Check specific pins
            output += f"**Specific GPIO Pins ({', '.join(map(str, pins))}):**\n"

            for pin in pins:
                exit_code, pin_info, _ = self.ssh.execute_command(
                    f"gpio -g mode {pin} 2>/dev/null; gpio -g read {pin} 2>/dev/null"
                )

                if exit_code == 0:
                    lines = pin_info.strip().split("\n")
                    mode = lines[0] if len(lines) > 0 else "unknown"
                    value = lines[1] if len(lines) > 1 else "unknown"
                    output += f"- **GPIO {pin}:** Mode={mode}, Value={value}\n"
                else:
                    output += f"- **GPIO {pin}:** Error reading pin\n"

        elif show_all:
            # Show all GPIO pins
            output += "**All GPIO Pin Status:**\n"

            exit_code, all_pins, _ = self.ssh.execute_command(
                "gpio readall 2>/dev/null"
            )

            if exit_code == 0:
                output += f"```\n{all_pins}\n```\n"
            else:
                output += "❌ Could not read GPIO pin status\n"

        else:
            # Show commonly used pins for hardware
            common_pins = {
                14: "PWM0 (Fan control)",
                15: "TXD (Serial/Fan)",
                18: "PWM0 (Fan/LED control)",
                23: "GPIO23 (Fan control)",
                24: "GPIO24 (Fan control)",
                25: "GPIO25 (Fan control)",
            }

            output += "**Common Hardware GPIO Pins:**\n"

            for pin, description in common_pins.items():
                exit_code, pin_info, _ = self.ssh.execute_command(
                    f"gpio -g mode {pin} 2>/dev/null; gpio -g read {pin} 2>/dev/null"
                )

                if exit_code == 0:
                    lines = pin_info.strip().split("\n")
                    mode = lines[0] if len(lines) > 0 else "unknown"
                    value = lines[1] if len(lines) > 1 else "unknown"
                    output += f"- **GPIO {pin}** ({description}): {mode}={value}\n"

        # Check for I2C devices
        output += "\n**I2C Devices:**\n"
        exit_code, i2c_devices, _ = self.ssh.execute_command(
            "i2cdetect -y 1 2>/dev/null | grep -E '[0-9a-f]{2}' || echo 'No I2C devices found'"
        )

        if "No I2C devices found" not in i2c_devices:
            output += f"```\n{i2c_devices}\n```\n"
        else:
            output += "No I2C devices detected\n"

        # Check SPI status
        output += "\n**SPI Status:**\n"
        exit_code, spi_status, _ = self.ssh.execute_command(
            "ls /dev/spidev* 2>/dev/null && echo 'SPI enabled' || echo 'SPI not enabled'"
        )

        output += f"{spi_status}\n"

        # GPIO usage recommendations
        output += "\n**GPIO Usage Notes:**\n"
        output += "- GPIO 14, 18: Hardware PWM (best for fan control)\n"
        output += "- GPIO 2, 3: I2C (SDA, SCL)\n"
        output += "- GPIO 8-11: SPI interface\n"
        output += "- GPIO 14, 15: UART (avoid if using serial console)\n"
        output += "- Use `gpio export` to control pins from scripts\n"

        return [TextContent(type="text", text=output)]
