"""SSH implementation of controller repository."""

import re
from typing import List

from ..domain.models import CommandResult
from ..domain.models import Controller
from ..domain.models import ControllerType
from ..domain.ports import ControllerRepository
from ..domain.ports import RetroPieClient


class SSHControllerRepository(ControllerRepository):
    """SSH implementation of controller repository interface."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def detect_controllers(self) -> List[Controller]:
        """Detect connected controllers."""
        # Use ls to check /dev/input/js* devices
        js_result = self._client.execute_command("ls -la /dev/input/js* 2>/dev/null")

        # Use lsusb to get more controller info
        usb_result = self._client.execute_command("lsusb")

        controllers = []

        # Parse joystick devices
        if js_result.success:
            js_devices = []
            for line in js_result.stdout.strip().split("\n"):
                if "/dev/input/js" in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        device_path = parts[-1]
                        js_devices.append(device_path)

            # For each joystick device, try to get more info
            for device in js_devices:
                # Extract device number
                device_num = device.replace("/dev/input/js", "")

                # Try to get device name from /proc/bus/input/devices
                name_result = self._client.execute_command(
                    f"cat /proc/bus/input/devices | grep -B 5 js{device_num} | grep Name | head -1"
                )

                name = "Unknown Controller"
                vendor_id = "0000"
                product_id = "0000"
                controller_type = ControllerType.UNKNOWN

                if name_result.success and name_result.stdout:
                    name_match = re.search(r'Name="([^"]+)"', name_result.stdout)
                    if name_match:
                        name = name_match.group(1)

                        # Determine controller type from name
                        name_lower = name.lower()
                        if "xbox" in name_lower:
                            controller_type = ControllerType.XBOX
                        elif "ps5" in name_lower or "dualsense" in name_lower:
                            controller_type = ControllerType.PS5
                        elif (
                            "playstation" in name_lower
                            or "ps4" in name_lower
                            or "dualshock" in name_lower
                            or ("sony" in name_lower and "wireless controller" in name_lower)
                        ):
                            controller_type = ControllerType.PS4
                        elif "nintendo" in name_lower or "switch pro" in name_lower:
                            controller_type = ControllerType.NINTENDO_PRO
                        elif "8bitdo" in name_lower:
                            controller_type = ControllerType.EIGHT_BIT_DO
                        else:
                            controller_type = ControllerType.GENERIC

                # Try to get vendor/product IDs from lsusb
                if usb_result.success and name != "Unknown Controller":
                    for usb_line in usb_result.stdout.strip().split("\n"):
                        if any(
                            keyword in usb_line.lower()
                            for keyword in [
                                "gamepad",
                                "controller",
                                "xbox",
                                "playstation",
                                "8bitdo",
                            ]
                        ):
                            id_match = re.search(
                                r"ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})", usb_line
                            )
                            if id_match:
                                vendor_id = id_match.group(1)
                                product_id = id_match.group(2)
                                break

                # Check if controller is configured in ES
                config_result = self._client.execute_command(
                    f"grep -q 'input_device.*{name}' /opt/retropie/configs/all/retroarch.cfg"
                )
                is_configured = config_result.success

                # Determine if special driver is needed
                driver_required = None
                if controller_type == ControllerType.XBOX:
                    # Check if xboxdrv is needed
                    xpad_result = self._client.execute_command("lsmod | grep -q xpad")
                    if not xpad_result.success:
                        driver_required = "xboxdrv"
                elif controller_type == ControllerType.PS4:
                    # Check if ds4drv is installed
                    ds4_result = self._client.execute_command("which ds4drv")
                    if not ds4_result.success:
                        driver_required = "ds4drv"

                controllers.append(
                    Controller(
                        name=name,
                        device_path=device,
                        controller_type=controller_type,
                        connected=True,
                        vendor_id=vendor_id,
                        product_id=product_id,
                        is_configured=is_configured,
                        driver_required=driver_required,
                    )
                )

        return controllers

    def setup_controller(self, controller: Controller) -> CommandResult:
        """Set up a controller with appropriate drivers."""
        commands = []

        # Install required driver if needed - ALL with explicit sudo prefix
        if controller.driver_required:
            if controller.driver_required == "xboxdrv":
                commands.extend(
                    [
                        "sudo apt-get update",
                        "sudo apt-get install -y xboxdrv",
                        "sudo systemctl enable xboxdrv",
                        "sudo systemctl start xboxdrv",
                    ]
                )
            elif controller.driver_required == "ds4drv":
                commands.extend(
                    [
                        "sudo apt-get update",
                        "sudo apt-get install -y python3-pip",
                        "sudo pip3 install ds4drv",
                    ]
                )

        # Configure controller in EmulationStation
        commands.append(
            f"sudo -u pi emulationstation --configure-input {controller.device_path}"
        )

        # Execute all commands - still use use_sudo=True for double safety
        if commands:
            full_command = " && ".join(commands)
            return self._client.execute_command(full_command, use_sudo=True)

        return CommandResult(
            command="",
            exit_code=0,
            stdout="Controller already configured",
            stderr="",
            success=True,
            execution_time=0.0,
        )

    def test_controller(self, controller: Controller) -> CommandResult:
        """Test controller functionality."""
        # Use jstest to test the controller
        command = f"timeout 5 jstest --normal {controller.device_path}"
        return self._client.execute_command(command)

    def configure_controller_mapping(
        self, controller: Controller, mapping: dict
    ) -> CommandResult:
        """Configure controller button mapping."""
        # Build retroarch config for the controller
        config_lines = [f'input_device = "{controller.name}"']

        # Add each mapping
        for button, value in mapping.items():
            config_lines.append(f'input_{button} = "{value}"')

        # Write to controller-specific config
        config_content = "\n".join(config_lines)
        config_path = (
            f"/opt/retropie/configs/all/retroarch/autoconfig/{controller.name}.cfg"
        )

        # Create the config file
        command = f"echo '{config_content}' > '{config_path}'"
        return self._client.execute_command(command, use_sudo=True)
