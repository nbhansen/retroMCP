"""Tests for Result pattern conversion in package use cases.

Following TDD approach - these tests will initially fail until use cases handle Result types.
"""

from unittest.mock import Mock

from retromcp.application.package_use_cases import InstallPackagesUseCase
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Package
from retromcp.domain.models import Result
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import SystemRepository


class TestInstallPackagesUseCaseResult:
    """Test Result pattern conversion in InstallPackagesUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_system_repo = Mock(spec=SystemRepository)
        self.use_case = InstallPackagesUseCase(self.mock_system_repo)

    def test_execute_returns_result_success_when_packages_installed(self):
        """Test that execute returns Result.success when packages are installed successfully."""
        # Arrange
        packages_to_install = ["vim", "htop"]

        # Mock get_packages to return no installed packages (Result pattern)
        self.mock_system_repo.get_packages.return_value = Result.success([])

        # Mock install_packages to return successful CommandResult (Result pattern)
        install_result = CommandResult(
            command="sudo apt-get install -y vim htop",
            exit_code=0,
            stdout="Installation successful",
            stderr="",
            success=True,
            execution_time=5.0,
        )
        self.mock_system_repo.install_packages.return_value = Result.success(
            install_result
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "Installation successful" in result.value.stdout

    def test_execute_returns_result_error_when_get_packages_fails(self):
        """Test that execute returns Result.error when get_packages fails."""
        # Arrange
        packages_to_install = ["vim"]

        # Mock get_packages to return error (Result pattern)
        get_packages_error = ExecutionError(
            code="PACKAGE_QUERY_FAILED",
            message="Failed to query packages",
            command="dpkg-query",
            exit_code=1,
            stderr="Database error",
        )
        self.mock_system_repo.get_packages.return_value = Result.error(
            get_packages_error
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "PACKAGE_QUERY_FAILED"
        assert "Failed to query packages" in result.error_or_none.message

    def test_execute_returns_result_error_when_install_packages_fails(self):
        """Test that execute returns Result.error when install_packages fails."""
        # Arrange
        packages_to_install = ["invalid-package"]

        # Mock get_packages to return no installed packages
        self.mock_system_repo.get_packages.return_value = Result.success([])

        # Mock install_packages to return error
        install_error = ExecutionError(
            code="PACKAGE_INSTALL_FAILED",
            message="Failed to install packages",
            command="sudo apt-get install -y invalid-package",
            exit_code=100,
            stderr="E: Unable to locate package invalid-package",
        )
        self.mock_system_repo.install_packages.return_value = Result.error(
            install_error
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "PACKAGE_INSTALL_FAILED"
        assert "invalid-package" in result.error_or_none.stderr

    def test_execute_returns_result_success_when_packages_already_installed(self):
        """Test that execute returns Result.success when all packages are already installed."""
        # Arrange
        packages_to_install = ["vim", "htop"]

        # Mock get_packages to return already installed packages
        installed_packages = [
            Package(name="vim", version="8.2", installed=True),
            Package(name="htop", version="3.0", installed=True),
        ]
        self.mock_system_repo.get_packages.return_value = Result.success(
            installed_packages
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "already installed" in result.value.stdout
        # install_packages should not be called
        self.mock_system_repo.install_packages.assert_not_called()

    def test_execute_returns_result_success_when_no_packages_specified(self):
        """Test that execute returns Result.success when no packages are specified."""
        # Arrange
        packages_to_install = []

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "No packages specified" in result.value.stdout
        # Repository methods should not be called
        self.mock_system_repo.get_packages.assert_not_called()
        self.mock_system_repo.install_packages.assert_not_called()

    def test_execute_filters_already_installed_packages(self):
        """Test that execute only installs packages that are not already installed."""
        # Arrange
        packages_to_install = ["vim", "htop", "curl"]

        # Mock get_packages to return some installed packages
        installed_packages = [
            Package(name="vim", version="8.2", installed=True),
            Package(name="git", version="2.3", installed=True),  # Not in request
            Package(
                name="curl", version="7.8", installed=False
            ),  # Not actually installed
        ]
        self.mock_system_repo.get_packages.return_value = Result.success(
            installed_packages
        )

        # Mock install_packages for remaining packages
        install_result = CommandResult(
            command="sudo apt-get install -y htop curl",
            exit_code=0,
            stdout="Installation successful",
            stderr="",
            success=True,
            execution_time=3.0,
        )
        self.mock_system_repo.install_packages.return_value = Result.success(
            install_result
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert result.is_success()
        # Should only install htop and curl (vim is already installed)
        self.mock_system_repo.install_packages.assert_called_once_with(["htop", "curl"])

    def test_execute_propagates_validation_errors_from_install_packages(self):
        """Test that execute propagates ValidationError from install_packages."""
        # Arrange
        packages_to_install = ["vim"]

        # Mock get_packages to return no installed packages
        self.mock_system_repo.get_packages.return_value = Result.success([])

        # Mock install_packages to return validation error
        validation_error = ValidationError(
            code="INVALID_INPUT",
            message="Packages parameter cannot be None",
            details={"parameter": "packages"},
        )
        self.mock_system_repo.install_packages.return_value = Result.error(
            validation_error
        )

        # Act
        result = self.use_case.execute(packages_to_install)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "INVALID_INPUT"
