"""Unit tests for enhanced package management error handling - Phase 2 Implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.package_management_tools import PackageManagementTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.system_tools
class TestPackageManagementErrorHandling:
    """Test enhanced error handling for package management according to PLAN.md Phase 2."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config

        # Mock use cases
        mock.install_packages_use_case = Mock()
        mock.install_packages_use_case.execute = Mock()
        mock.update_system_use_case = Mock()
        mock.update_system_use_case.execute = Mock()

        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )

        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def package_tools(self, mock_container: Mock) -> PackageManagementTools:
        """Provide PackageManagementTools instance with mocked dependencies."""
        return PackageManagementTools(mock_container)

    @pytest.mark.asyncio
    async def test_check_non_existent_package_shows_specific_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that checking a non-existent package shows a specific error message.
        
        According to PLAN.md: "Non-existent package check: ❌ Empty error message"
        This should provide clear, specific feedback for each package.
        """
        # Mock individual package check - package not installed
        def mock_execute_command(command: str) -> CommandResult:
            if "dpkg -l non-existent-package" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="",  # Empty output means not installed
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            elif "apt-cache show non-existent-package" in command:
                # Package doesn't exist in repository
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="E: No packages found",
                    success=False,
                    execution_time=0.3,
                )
            else:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="Unknown command",
                    success=False,
                    execution_time=0.1,
                )

        package_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["non-existent-package"],
            },
        )

        # Verify specific error message (not empty)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Should contain specific information about the non-existent package
        assert "Package Status Check:" in result[0].text
        assert "non-existent-package" in result[0].text
        assert "Not installed" in result[0].text or "not found" in result[0].text.lower()
        assert "❌" in result[0].text
        
        # Should NOT be a generic error message
        assert "failed to check packages" not in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_mixed_valid_invalid_packages_shows_all_statuses(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that checking mixed valid/invalid packages shows status for ALL packages.
        
        According to PLAN.md: "Mixed valid/invalid arrays: ❌ Fails entire operation"
        This should continue checking all packages and provide comprehensive status.
        """
        # Mock individual package checks
        def mock_execute_command(command: str) -> CommandResult:
            if "dpkg -l python3" in command and "grep '^ii'" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="ii  python3        3.9.2  amd64  Interactive high-level object-oriented language",
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            elif "dpkg -l non-existent-package" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="",  # Not installed
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            elif "apt-cache show non-existent-package" in command:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="E: No packages found",
                    success=False,
                    execution_time=0.3,
                )
            elif "dpkg -l vim" in command and "grep '^ii'" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="ii  vim            8.2.2434  amd64  Vi IMproved - enhanced vi editor",
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            else:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="Unknown command",
                    success=False,
                    execution_time=0.1,
                )

        package_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute package check with mixed valid/invalid packages
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["python3", "non-existent-package", "vim"],
            },
        )

        # Verify comprehensive status report
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Should show status for ALL packages
        assert "Package Status Check:" in result[0].text
        assert "✅ python3: Installed" in result[0].text
        assert "❌ non-existent-package: Not installed" in result[0].text
        assert "✅ vim: Installed" in result[0].text
        
        # Should include summary with counts
        assert "Summary:" in result[0].text
        assert "2/3 installed" in result[0].text
        assert "1/3 not installed" in result[0].text
        
        # Should NOT fail the entire operation
        assert "failed to check packages" not in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_multiple_non_existent_packages_shows_individual_status(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that checking multiple non-existent packages shows individual status for each."""
        # Mock individual package checks
        def mock_execute_command(command: str) -> CommandResult:
            if "dpkg -l" in command and any(pkg in command for pkg in ["fake-package-1", "fake-package-2", "fake-package-3"]):
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="",  # All not installed
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            elif "apt-cache show" in command:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="E: No packages found",
                    success=False,
                    execution_time=0.3,
                )
            else:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="Unknown command",
                    success=False,
                    execution_time=0.1,
                )

        package_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["fake-package-1", "fake-package-2", "fake-package-3"],
            },
        )

        # Verify individual status for each package
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Should show individual status
        assert "❌ fake-package-1: Not installed" in result[0].text
        assert "❌ fake-package-2: Not installed" in result[0].text
        assert "❌ fake-package-3: Not installed" in result[0].text
        
        # Should include summary
        assert "Summary: 0/3 installed" in result[0].text
        assert "3/3 not installed" in result[0].text

    @pytest.mark.asyncio
    async def test_check_packages_with_dpkg_errors_shows_warning(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that packages with dpkg errors show warning status."""
        # Mock command failure for one package
        def mock_execute_command(command: str) -> CommandResult:
            if "dpkg -l error-package" in command:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="dpkg: error accessing database",
                    success=False,
                    execution_time=0.5,
                )
            elif "dpkg -l good-package" in command and "grep '^ii'" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="ii  good-package   1.0.0  amd64  A good package",
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            else:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="Unknown command",
                    success=False,
                    execution_time=0.1,
                )

        package_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["good-package", "error-package"],
            },
        )

        # Verify shows warning for error package
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        assert "✅ good-package: Installed" in result[0].text
        assert "⚠️ error-package: Check failed" in result[0].text
        
        # Should include error count in summary
        assert "1/2 installed" in result[0].text
        assert "1/2 check failed" in result[0].text

    @pytest.mark.asyncio
    async def test_check_single_package_does_not_show_summary(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that checking a single package doesn't show redundant summary."""
        # Mock single package check
        def mock_execute_command(command: str) -> CommandResult:
            if "dpkg -l python3" in command and "grep '^ii'" in command:
                return CommandResult(
                    command=command,
                    exit_code=0,
                    stdout="ii  python3        3.9.2  amd64  Interactive high-level object-oriented language",
                    stderr="",
                    success=True,
                    execution_time=0.5,
                )
            else:
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="Unknown command",
                    success=False,
                    execution_time=0.1,
                )

        package_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute single package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["python3"],
            },
        )

        # Verify no redundant summary for single package
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        assert "✅ python3: Installed" in result[0].text
        # Should NOT include summary for single package
        assert "Summary:" not in result[0].text