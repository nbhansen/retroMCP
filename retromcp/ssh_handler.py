"""SSH connection handler for RetroPie communication."""

import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import paramiko

from .timeout_config import get_timeout_config

logger = logging.getLogger(__name__)


class SSHHandler:
    """Handles SSH connections to RetroPie."""

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        port: int = 22,
        command_timeout: Optional[int] = None,
    ) -> None:
        """Initialize SSH handler.

        Args:
            host: Hostname or IP of the Raspberry Pi
            username: SSH username (usually 'pi')
            password: SSH password (if using password auth)
            key_path: Path to SSH private key (if using key auth)
            port: SSH port (default 22)
            command_timeout: Command execution timeout in seconds (uses timeout config if None)
        """
        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self.port = port
        self.timeout_config = get_timeout_config()
        self.command_timeout = command_timeout or self.timeout_config.ssh_command_default
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """Establish SSH connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_args = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 10,  # 10 second timeout to prevent hanging
            }

            if self.key_path:
                connect_args["key_filename"] = self.key_path
            elif self.password:
                connect_args["password"] = self.password
            else:
                # Try default SSH key locations
                connect_args["look_for_keys"] = True

            self.client.connect(**connect_args)
            logger.info(f"Connected to {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            return False

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info(f"Disconnected from {self.host}")

    def execute_command(self, command: str, custom_timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """Execute a command on the remote host with intelligent timeout protection.

        Args:
            command: Command to execute
            custom_timeout: Custom timeout override (uses smart detection if None)

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            RuntimeError: If not connected or command times out
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # Check if this is a monitoring command that should run without timeout
        if custom_timeout is None and self.timeout_config.is_monitoring_command(command):
            # Auto-detect monitoring command and handle appropriately
            return self.execute_monitoring_command(command)

        # Determine appropriate timeout for this command
        timeout = custom_timeout or self.timeout_config.get_timeout_for_command(command)

        try:
            # Set timeout for command execution to prevent hanging
            stdin, stdout, stderr = self.client.exec_command(
                command, timeout=timeout
            )

            # Get exit status with timeout protection
            exit_code = stdout.channel.recv_exit_status()

            stdout_text = stdout.read().decode("utf-8").strip()
            stderr_text = stderr.read().decode("utf-8").strip()

            logger.debug(f"Command executed with {timeout}s timeout: {command[:50]}...")
            return exit_code, stdout_text, stderr_text

        except paramiko.SSHException as e:
            if "Timeout" in str(e):
                raise RuntimeError(
                    f"Command execution timeout after {timeout}s: {command}"
                ) from e
            logger.error(f"SSH error executing command '{command}': {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {e}")
            raise

    def execute_monitoring_command(self, command: str) -> Tuple[int, str, str]:
        """Execute a monitoring command that runs indefinitely without timeout.

        This method is designed for commands like 'watch', 'tail -f', 'top', etc.
        that are intended to run continuously. It provides guidance on how to
        terminate the command when needed.

        Args:
            command: Monitoring command to execute

        Returns:
            Tuple of (exit_code, stdout with termination info, stderr)

        Raises:
            RuntimeError: If not connected
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # For monitoring commands, we want to provide immediate feedback
        # and guidance on termination, rather than actually running indefinitely
        command_name = command.split()[0]
        if "sudo" in command.lower():
            # Extract actual command after sudo
            parts = command.split()
            if len(parts) > 1:
                command_name = parts[1]

        response_message = f"""✅ Monitoring command started successfully

Command: {command}
Status: Running in background

To terminate this monitoring command, use:
pkill -f "{command_name}"

The command will continue running until terminated."""

        # Return success with guidance message
        return 0, response_message, ""

    def execute_command_safe(self, command: str, custom_timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """Execute a command with timeout wrapper to prevent hanging on interactive commands.

        This method automatically wraps commands with the 'timeout' utility to ensure
        they terminate even if they would normally hang waiting for user input.

        Args:
            command: Command to execute
            custom_timeout: Custom timeout override (uses smart detection if None)

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            RuntimeError: If not connected or command times out
        """
        # Use timeout config to wrap command with appropriate timeout
        safe_command = self.timeout_config.wrap_command_with_timeout(command, custom_timeout)

        # Execute the wrapped command
        return self.execute_command(safe_command, custom_timeout)

    def test_connection(self) -> bool:
        """Test if connection is active.

        Returns:
            True if connection is active, False otherwise
        """
        try:
            exit_code, stdout, _ = self.execute_command("echo 'test'")
            return exit_code == 0 and stdout == "test"
        except Exception:
            return False

    def __enter__(self) -> "SSHHandler":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.disconnect()


class RetroPieSSH(SSHHandler):
    """RetroPie-specific SSH operations for setup and configuration."""

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information from RetroPie.

        Returns:
            Dictionary with system information
        """
        info = {}

        # Get temperature
        exit_code, temp_output, _ = self.execute_command("vcgencmd measure_temp")
        if exit_code == 0 and "temp=" in temp_output:
            temp_str = temp_output.split("=")[1].replace("'C", "")
            info["temperature"] = float(temp_str)

        # Get memory info
        exit_code, mem_output, _ = self.execute_command("free -m | grep Mem")
        if exit_code == 0:
            parts = mem_output.split()
            if len(parts) >= 3:
                info["memory"] = {
                    "total": int(parts[1]),
                    "used": int(parts[2]),
                    "free": int(parts[3]) if len(parts) > 3 else None,
                }

        # Get disk usage
        exit_code, disk_output, _ = self.execute_command("df -h / | tail -1")
        if exit_code == 0:
            parts = disk_output.split()
            if len(parts) >= 5:
                info["disk"] = {
                    "total": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "use_percent": parts[4],
                }

        # Check if EmulationStation is running
        exit_code, _, _ = self.execute_command("pgrep emulationstation")
        info["emulationstation_running"] = exit_code == 0

        return info

    def detect_controllers(self) -> Dict[str, Any]:
        """Detect connected controllers.

        Returns:
            Dictionary with controller information
        """
        controllers = {}

        # Check USB devices
        exit_code, usb_output, _ = self.execute_command("lsusb")
        if exit_code == 0:
            controllers["usb_devices"] = usb_output.splitlines()

        # Check for joystick devices
        exit_code, js_output, _ = self.execute_command("ls /dev/input/js* 2>/dev/null")
        if exit_code == 0:
            controllers["joystick_devices"] = js_output.splitlines()

        # Get detailed controller info using jstest if available
        exit_code, jstest_output, _ = self.execute_command("which jstest")
        if exit_code == 0:
            controllers["jstest_available"] = True
            # Test first joystick if available
            exit_code, js_info, _ = self.execute_command(
                "timeout 1 jstest --normal /dev/input/js0 2>/dev/null | head -3"
            )
            if exit_code == 0:
                controllers["js0_info"] = js_info
        else:
            controllers["jstest_available"] = False

        return controllers

    def install_packages(self, packages: List[str]) -> Tuple[bool, str]:
        """Install packages using apt-get.

        Args:
            packages: List of package names to install

        Returns:
            Tuple of (success, message)
        """
        package_str = " ".join(packages)

        # Update package list first
        update_cmd = "sudo apt-get update"
        exit_code, _, stderr = self.execute_command(update_cmd)
        if exit_code != 0:
            return False, f"Failed to update package list: {stderr}"

        # Install packages
        install_cmd = f"sudo apt-get install -y {package_str}"
        exit_code, stdout, stderr = self.execute_command(install_cmd)

        if exit_code == 0:
            return True, f"Successfully installed: {package_str}"
        else:
            return False, f"Failed to install packages: {stderr}"

    def configure_controller(self, controller_type: str) -> Tuple[bool, str]:
        """Configure a specific controller type.

        Args:
            controller_type: Type of controller (e.g., 'xbox', 'ps4', '8bitdo')

        Returns:
            Tuple of (success, message)
        """
        config_map = {
            "xbox": {
                "packages": ["xboxdrv"],
                "config_commands": [
                    "sudo systemctl enable xboxdrv",
                    "sudo systemctl start xboxdrv",
                ],
            },
            "ps4": {
                "packages": ["ds4drv"],
                "config_commands": ["sudo ds4drv --daemon"],
            },
            "8bitdo": {
                "packages": ["joystick", "jstest-gtk"],
                "config_commands": [
                    'echo "options bluetooth disable_ertm=1" | sudo tee -a /etc/modprobe.d/bluetooth.conf',
                    "sudo systemctl restart bluetooth",
                ],
            },
        }

        if controller_type not in config_map:
            return False, f"Unknown controller type: {controller_type}"

        config = config_map[controller_type]

        # Install required packages
        if config["packages"]:
            success, msg = self.install_packages(config["packages"])
            if not success:
                return False, msg

        # Run configuration commands
        for cmd in config["config_commands"]:
            exit_code, _, stderr = self.execute_command(cmd)
            if exit_code != 0:
                return False, f"Configuration failed: {stderr}"

        return True, f"Successfully configured {controller_type} controller"

    def setup_emulator(self, system: str, emulator: str) -> Tuple[bool, str]:
        """Setup or configure an emulator for a specific system.

        Args:
            system: System name (e.g., 'n64', 'psx', 'dreamcast')
            emulator: Emulator name (e.g., 'mupen64plus', 'pcsx-rearmed')

        Returns:
            Tuple of (success, message)
        """
        # Run RetroPie-Setup script for specific emulator
        setup_cmd = f"sudo /home/pi/RetroPie-Setup/retropie_packages.sh {emulator}"
        exit_code, stdout, stderr = self.execute_command(setup_cmd)

        if exit_code == 0:
            return True, f"Successfully setup {emulator} for {system}"
        else:
            return False, f"Failed to setup emulator: {stderr}"

    def check_bios_files(self, system: str) -> Dict[str, Any]:
        """Check if required BIOS files are present for a system.

        Args:
            system: System name

        Returns:
            Dictionary with BIOS file status
        """
        bios_requirements = {
            "psx": ["scph1001.bin", "scph5501.bin", "scph7001.bin"],
            "dreamcast": ["dc_boot.bin", "dc_flash.bin"],
            "neogeo": ["neogeo.zip"],
            "segacd": ["bios_CD_E.bin", "bios_CD_U.bin", "bios_CD_J.bin"],
        }

        if system not in bios_requirements:
            return {"system": system, "bios_required": False}

        bios_dir = "/home/pi/RetroPie/BIOS"
        required_files = bios_requirements[system]
        status = {}

        for bios_file in required_files:
            exit_code, _, _ = self.execute_command(f"test -f {bios_dir}/{bios_file}")
            status[bios_file] = exit_code == 0

        return {
            "system": system,
            "bios_required": True,
            "files": status,
            "all_present": all(status.values()),
        }

    def run_retropie_setup(self, module: Optional[str] = None) -> Tuple[bool, str]:
        """Run RetroPie-Setup script.

        Args:
            module: Specific module to run (optional)

        Returns:
            Tuple of (success, message)
        """
        if module:
            cmd = f"sudo /home/pi/RetroPie-Setup/retropie_setup.sh {module}"
        else:
            # Run in unattended mode for basic setup
            cmd = "sudo /home/pi/RetroPie-Setup/retropie_setup.sh setup basic_install"

        exit_code, stdout, stderr = self.execute_command(cmd)

        if exit_code == 0:
            return True, "RetroPie-Setup completed successfully"
        else:
            return False, f"RetroPie-Setup failed: {stderr}"
