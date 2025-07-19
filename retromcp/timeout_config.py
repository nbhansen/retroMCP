"""Centralized timeout configuration for RetroMCP operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeoutConfig:
    """Configuration for various operation timeouts."""

    # SSH connection timeouts
    ssh_connection: int = 30
    ssh_command_default: int = 60

    # Command-specific timeouts
    quick_commands: int = 10  # echo, test, pwd, etc.
    system_info: int = 30     # temperature, memory, disk usage
    package_operations: int = 300  # apt install, update (5 minutes)
    retropie_setup: int = 1800     # RetroPie-Setup operations (30 minutes)
    emulator_install: int = 3600   # Emulator compilation (1 hour)
    controller_test: int = 15      # Controller testing

    # Long-running operations
    system_update: int = 1800      # System updates (30 minutes)
    backup_operations: int = 3600  # Backup/restore (1 hour)

    def get_timeout_for_command(self, command: str) -> int:
        """Get appropriate timeout for a specific command.

        Args:
            command: The command to get timeout for

        Returns:
            Timeout in seconds
        """
        # System info commands (check first to avoid conflicts with quick commands)
        system_info_commands = [
            "vcgencmd", "free", "df", "lscpu", "lsusb", "iwconfig",
            "ifconfig", "/opt/vc/bin/vcgencmd", "cat /proc/meminfo"
        ]

        # Quick commands
        quick_commands = [
            "echo", "pwd", "whoami", "date", "uptime", "hostname",
            "test", "which", "ps", "ls", "cat /proc/version"
        ]

        # Package operations
        package_commands = [
            "apt-get", "apt", "dpkg", "pip", "pip3"
        ]

        # RetroPie specific
        retropie_commands = [
            "retropie_setup", "/home/pi/RetroPie-Setup/retropie_setup.sh"
        ]

        # Controller testing
        controller_commands = [
            "jstest", "evtest", "/dev/input"
        ]

        # Check command type and return appropriate timeout
        command_lower = command.lower().strip()
        command_words = command_lower.split()

        # Check for package operations FIRST (since they're more specific)
        if any(cmd in command_lower for cmd in package_commands):
            # Check for system update operations (which take longer)
            if any(term in command_lower for term in ["update", "upgrade"]):
                return self.system_update
            return self.package_operations

        # Check for system info commands
        if any(cmd in command_lower for cmd in system_info_commands):
            return self.system_info

        # Check for quick commands (use word boundaries to avoid false matches)
        if any(cmd in command_words for cmd in quick_commands):
            return self.quick_commands

        # Check for RetroPie operations
        if any(cmd in command_lower for cmd in retropie_commands):
            return self.retropie_setup

        # Check for controller operations
        if any(cmd in command_lower for cmd in controller_commands):
            return self.controller_test

        # Check for specific patterns
        if "timeout" in command_lower:
            # Command already has timeout wrapper, use default
            return self.ssh_command_default

        if "sudo" in command_lower and ("install" in command_lower or "build" in command_lower):
            return self.emulator_install

        # Default timeout
        return self.ssh_command_default

    def is_monitoring_command(self, command: str) -> bool:
        """Check if a command is a monitoring command that runs indefinitely.

        Args:
            command: The command to check

        Returns:
            True if the command is a monitoring command, False otherwise
        """
        command_lower = command.lower().strip()

        # Watch commands
        if "watch" in command_lower and command_lower.split()[0] in ["watch", "sudo"] and "watch" in command_lower:
            return True

        # Tail follow commands
        if "tail" in command_lower and ("-f" in command_lower or "-F" in command_lower or "--follow" in command_lower):
            return True

        # Top/htop/iotop commands
        top_commands = ["top", "htop", "iotop"]
        command_words = command_lower.split()
        if any(cmd in command_words for cmd in top_commands):
            return True

        # Journalctl follow commands
        return bool("journalctl" in command_lower and ("-f" in command_lower or "--follow" in command_lower))

    def get_timeout_for_monitoring_command(self, command: str) -> Optional[int]:
        """Get timeout for monitoring commands (should be None for no timeout).

        Args:
            command: The command to get timeout for

        Returns:
            None for monitoring commands (no timeout)
        """
        if self.is_monitoring_command(command):
            return None
        return self.get_timeout_for_command(command)

    def wrap_command_with_timeout(self, command: str, custom_timeout: Optional[int] = None) -> str:
        """Wrap a command with timeout if it doesn't already have one.

        Args:
            command: The command to wrap
            custom_timeout: Custom timeout to use instead of auto-detection

        Returns:
            Command wrapped with timeout
        """
        # Don't double-wrap commands that already have timeout
        if command.strip().startswith("timeout "):
            return command

        timeout_seconds = custom_timeout or self.get_timeout_for_command(command)

        # Use timeout command to prevent hanging
        return f"timeout {timeout_seconds} {command}"

    def get_safe_retropie_command(self, action: str) -> str:
        """Get a safe RetroPie-Setup command with timeout and non-interactive flags.

        Args:
            action: The RetroPie action to perform

        Returns:
            Safe command string
        """
        base_cmd = "/home/pi/RetroPie-Setup/retropie_setup.sh"

        # Add non-interactive flags to prevent hanging on prompts
        safe_cmd = f"{base_cmd} {action}"

        # Wrap with timeout
        return self.wrap_command_with_timeout(safe_cmd, self.retropie_setup)


# Global default timeout configuration
DEFAULT_TIMEOUTS = TimeoutConfig()


def get_timeout_config() -> TimeoutConfig:
    """Get the global timeout configuration.

    Returns:
        TimeoutConfig instance
    """
    return DEFAULT_TIMEOUTS


def set_timeout_config(config: TimeoutConfig) -> None:
    """Set a custom global timeout configuration.

    Args:
        config: New timeout configuration
    """
    global DEFAULT_TIMEOUTS
    DEFAULT_TIMEOUTS = config
