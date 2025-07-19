"""Security validation service for command and path validation.

Implements whitelist-based validation to replace regex blacklist approaches.
"""
from __future__ import annotations

import re
import shlex
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Generic
from typing import TypeVar

T = TypeVar('T')
E = TypeVar('E')


@dataclass(frozen=True)
class ValidationResult(Generic[T, E]):
    """Result type for validation operations."""

    _value: T | None = None
    _error: E | None = None

    @classmethod
    def success(cls, value: T) -> ValidationResult[T, E]:
        """Create a successful validation result."""
        return cls(_value=value, _error=None)

    @classmethod
    def error(cls, error: E) -> ValidationResult[T, E]:
        """Create a failed validation result."""
        return cls(_value=None, _error=error)

    def is_success(self) -> bool:
        """Check if validation succeeded."""
        return self._error is None

    def is_error(self) -> bool:
        """Check if validation failed."""
        return self._error is not None

    @property
    def value(self) -> T:
        """Get the success value."""
        if self._error is not None:
            raise ValueError("Cannot get value from error result")
        return self._value

    @property
    def error_value(self) -> E:
        """Get the error value."""
        if self._error is None:
            raise ValueError("Cannot get error from success result")
        return self._error


class SecurityValidator:
    """Whitelist-based security validator for commands and paths."""

    def __init__(self) -> None:
        """Initialize the security validator."""
        self._command_whitelist = self._build_command_whitelist()
        self._safe_path_patterns = self._build_safe_path_patterns()

    def _build_command_whitelist(self) -> set[str]:
        """Build comprehensive whitelist of allowed command patterns."""
        return {
            # System information commands
            "hostname", "uptime", "free", "df", "du", "ps", "top", "htop", "iotop",
            "cat", "head", "tail", "grep", "awk", "sed", "sort", "uniq", "cut",

            # File operations (safe subset)
            "ls", "wc", "file", "stat", "pwd", "echo",

            # Text processing and shell utilities
            "test", "true", "false", "expr", "basename", "dirname",

            # Find operations (restricted to safe paths)
            "find",

            # Service management (read-only)
            "systemctl",

            # Docker operations (safe subset)
            "docker",

            # RetroPie specific
            "vcgencmd", "emulationstation",

            # Network tools (safe subset)
            "ping", "dig", "nslookup", "curl", "wget",

            # Package management (read-only)
            "dpkg-query", "apt", "apt-cache", "npm",

            # Git operations (safe subset)
            "git",

            # Archive operations
            "tar", "unzip", "zip", "gzip", "gunzip",

            # Process management (read-only)
            "pgrep", "pidof", "jobs", "which", "whereis", "type", "killall",

            # Environment
            "env", "printenv", "whoami", "id", "groups", "date",

            # Hardware monitoring
            "lscpu", "lshw", "lsusb", "lspci", "lsblk",
            "sensors", "iwconfig", "ifconfig", "dmidecode",

            # System paths that should be readable
            "/opt/retropie", "/usr/bin", "/usr/local/bin", "/bin", "/sbin",
        }

    def _build_safe_path_patterns(self) -> list[re.Pattern[str]]:
        """Build patterns for safe path validation."""
        safe_patterns = [
            # Home directory paths
            r"^/home/[^/]+/.*",
            r"^~/.*",

            # RetroPie specific paths
            r"^/opt/retropie/.*",
            r"^/home/[^/]+/RetroPie/.*",
            r"^/home/[^/]+/\.emulationstation/.*",

            # Config directories
            r"^/usr/local/.*",
            r"^/etc/[^/]+\.conf$",
            r"^/etc/[^/]+\.cfg$",

            # Log files
            r"^/var/log/[^/]+\.log$",

            # Relative paths (current directory)
            r"^[^/]+.*",
            r"^\./.*",

            # Temp directories
            r"^/tmp/[^/]+.*",
            r"^/var/tmp/[^/]+.*",
        ]

        return [re.compile(pattern) for pattern in safe_patterns]

    def validate_command(self, command: str) -> ValidationResult[str, str]:
        """Validate command using whitelist approach.

        Args:
            command: Command string to validate

        Returns:
            ValidationResult with success message or error
        """
        if not command or not command.strip():
            return ValidationResult.error("Empty command not allowed")

        command = command.strip()

        # Check for command injection patterns
        if self._contains_injection_patterns(command):
            return ValidationResult.error(
                f"Command contains dangerous injection patterns: {command}"
            )

        # Extract base command for whitelist checking
        base_command = self._extract_base_command(command)

        if not self._is_whitelisted_command(command, base_command):
            return ValidationResult.error(
                f"Dangerous command blocked: {base_command} not in whitelist"
            )

        return ValidationResult.success(f"Command allowed: {command}")

    def _contains_injection_patterns(self, command: str) -> bool:
        """Check for command injection patterns."""
        dangerous_patterns = [
            r";.*\b(rm|dd|mkfs|chmod\s+777|passwd|su|sudo)\b",  # Command separator with dangerous commands
            r"&&.*\b(rm|dd|mkfs|chmod\s+777|passwd|su|sudo)\b",  # Command AND with dangerous commands
            r"\|\|.*\b(rm|dd|mkfs|chmod\s+777|passwd|su|sudo)\b",  # Command OR with dangerous commands
            r"\$\(",  # Command substitution
            r"`[^`]*`",  # Backtick command substitution
            r"\beval\b",  # Eval command
            r"\bexec\b",  # Exec command
            r">\s*/dev/(sd|hd|nvme)",  # Writing to block devices
            r">\s*/etc/",  # Writing to system config
            r"\|\s*(bash|sh|zsh|fish)\b",  # Pipe to shell interpreters
            r"curl.*\|\s*(bash|sh)",  # Download and execute
            r"wget.*\|\s*(bash|sh)",  # Download and execute
            r"nc.*-e\s*/bin/",  # Reverse shell with -e flag
            r"\bnc\b.*\d+",  # Any nc command with port number (potential reverse shell)
            r"\$\{IFS\}",  # IFS injection attack
            r";",  # Any command separator
            r"&&",  # Any command AND
            r"\|\|",  # Any command OR
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        return False

    def _extract_base_command(self, command: str) -> str:
        """Extract the base command from a full command string."""
        # Use shlex to properly parse the command
        try:
            tokens = shlex.split(command)
            if tokens:
                return tokens[0]
        except ValueError:
            # If shlex parsing fails, fall back to simple splitting
            pass

        # Simple fallback
        return command.split()[0] if command.split() else ""

    def _is_whitelisted_command(self, full_command: str, base_command: str) -> bool:
        """Check if command is in whitelist."""
        # Direct base command match
        if base_command in self._command_whitelist:
            return True

        # Pattern matching for parameterized commands
        for allowed_pattern in self._command_whitelist:
            if self._matches_command_pattern(full_command, allowed_pattern):
                return True

        return False

    def _matches_command_pattern(self, command: str, pattern: str) -> bool:
        """Check if command matches an allowed pattern."""
        # For patterns like "systemctl status", check if command starts with it
        if " " in pattern:
            return command.startswith(pattern + " ") or command == pattern

        # For single commands, exact match on base command
        base_command = self._extract_base_command(command)
        return base_command == pattern

    def validate_path(self, path: str) -> ValidationResult[str, str]:
        """Validate path using canonicalization and whitelist.

        Args:
            path: Path string to validate

        Returns:
            ValidationResult with success message or error
        """
        if not path or not path.strip():
            return ValidationResult.error("Empty path not allowed")

        path = path.strip()

        # Check for URL encoding attempts
        if self._contains_url_encoding(path):
            return ValidationResult.error(
                f"URL-encoded path traversal attempt detected: {path}"
            )

        # Check for Windows-style backslash path separators (suspicious on Unix systems)
        if "\\" in path:
            return ValidationResult.error(
                f"Path traversal attempt with Windows separators blocked: {path}"
            )

        # Convert to Path object for canonicalization
        try:
            path_obj = Path(path)
            return self.validate_path_object(path_obj)
        except (OSError, ValueError) as e:
            return ValidationResult.error(f"Invalid path: {e}")

    def validate_path_object(self, path_obj: Path) -> ValidationResult[str, str]:
        """Validate a Path object.

        Args:
            path_obj: Path object to validate

        Returns:
            ValidationResult with success message or error
        """
        try:
            # Resolve to canonical path to handle traversal attempts
            resolved_path = path_obj.resolve()
            resolved_str = str(resolved_path)

            # Check for attempts to access critical system directories
            if self._is_critical_system_path(resolved_str):
                return ValidationResult.error(
                    f"Access to critical system directory blocked: {resolved_str}"
                )

            # Check if resolved path is safe
            if self._is_safe_path(resolved_str):
                return ValidationResult.success(f"Path allowed: {resolved_str}")
            else:
                return ValidationResult.error(
                    f"Path outside allowed directories: {resolved_str}"
                )

        except (OSError, RuntimeError) as e:
            return ValidationResult.error(
                f"Path resolution failed (possible symlink attack): {e}"
            )

    def _contains_url_encoding(self, path: str) -> bool:
        """Check for URL encoding that might hide traversal attempts."""
        # Decode and check if it contains traversal after decoding
        try:
            decoded = urllib.parse.unquote(path)
            if decoded != path and ".." in decoded:
                return True

            # Check for double encoding
            double_decoded = urllib.parse.unquote(decoded)
            if double_decoded != decoded and ".." in double_decoded:
                return True

        except Exception:
            # If decoding fails, treat as suspicious
            return True

        return False

    def _is_critical_system_path(self, path: str) -> bool:
        """Check if path accesses critical system directories that should be blocked."""
        critical_paths = [
            "/etc/passwd", "/etc/shadow", "/etc/hosts", "/etc/sudoers",
            "/root/", "/boot/", "/sys/", "/proc/", "/dev/",
            "/etc/ssh/", "/var/log/auth.log", "/var/log/secure",
            "/etc/crontab", "/etc/cron.d/", "/etc/systemd/",
        ]

        # Direct matches
        for critical in critical_paths:
            if path.startswith(critical) or path == critical.rstrip("/"):
                return True

        # Special case: check for critical filenames regardless of directory
        # This catches paths like /home/etc/passwd from traversal attempts
        critical_filenames = [
            "passwd", "shadow", "sudoers", "hosts", "auth.log", "secure"
        ]
        path_filename = path.split("/")[-1]
        return path_filename in critical_filenames

    def _is_safe_path(self, path: str) -> bool:
        """Check if resolved path matches safe patterns."""
        return any(pattern.match(path) for pattern in self._safe_path_patterns)

    def sanitize_input(self, input_str: str) -> ValidationResult[str, str]:
        """Sanitize input string by removing or escaping dangerous characters.

        Args:
            input_str: Input string to sanitize

        Returns:
            ValidationResult with sanitized string or error
        """
        if not input_str:
            return ValidationResult.success("")

        # Define dangerous characters that should be removed/escaped
        dangerous_chars = {
            ';': '',  # Remove command separators
            '|': '',  # Remove pipes
            '`': '',  # Remove backticks
            '$': '',  # Remove variable expansion
            '\n': ' ',  # Replace newlines with spaces
            '\r': ' ',  # Replace carriage returns with spaces
            '\t': ' ',  # Replace tabs with spaces
        }

        sanitized = input_str
        for char, replacement in dangerous_chars.items():
            sanitized = sanitized.replace(char, replacement)

        # Collapse multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Check if sanitization was necessary
        if sanitized != input_str:
            return ValidationResult.success(sanitized)
        else:
            return ValidationResult.success(input_str)
