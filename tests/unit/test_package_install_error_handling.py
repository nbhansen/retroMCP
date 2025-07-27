"""Unit tests for package installation error handling - Phase 2 Implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult, ExecutionError, Result
from retromcp.tools.package_management_tools import PackageManagementTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.system_tools
class TestPackageInstallErrorHandling:
    """Test enhanced error handling for package installation according to PLAN.md Phase 2."""

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
    async def test_install_non_existent_package_shows_specific_package_name(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that installing a non-existent package shows the specific package name in error.
        
        According to PLAN.md: The error message should include specific package names.
        """
        # Mock failed installation with generic error
        install_error = ExecutionError(
            code="PACKAGE_INSTALL_FAILED",
            message="Package installation failed: E: Unable to locate package",  # Generic error
            command="sudo apt-get install -y fake-nonexistent-package",
            exit_code=100,
            stderr="E: Unable to locate package fake-nonexistent-package",
        )
        package_tools.container.install_packages_use_case.execute.return_value = Result.error(
            install_error
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["fake-nonexistent-package"],
            },
        )

        # Verify error contains specific package name
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "fake-nonexistent-package" in result[0].text
        # Should NOT just say "Package installation failed" with no specifics
        assert result[0].text != "❌ Error: Package installation failed"

    @pytest.mark.asyncio
    async def test_install_mixed_packages_shows_individual_results(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that installing mixed valid/invalid packages shows results for each.
        
        According to PLAN.md: "Mixed valid/invalid arrays: ❌ Fails entire operation"
        This should be fixed to show individual results.
        """
        # For this test, we need to enhance the use case to return detailed results
        # Currently it returns a single CommandResult, but we need per-package results
        
        # Mock the use case to return an error that contains information about which packages failed
        install_error = ExecutionError(
            code="PARTIAL_INSTALL_FAILURE",
            message="Some packages failed to install",
            command="sudo apt-get install -y python3 fake-package vim",
            exit_code=100,
            stderr="E: Unable to locate package fake-package",
            details={
                "succeeded": ["python3", "vim"],
                "failed": ["fake-package"],
                "total": 3
            }
        )
        package_tools.container.install_packages_use_case.execute.return_value = Result.error(
            install_error
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["python3", "fake-package", "vim"],
            },
        )

        # Verify comprehensive result reporting
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Should show which packages succeeded and which failed
        assert "python3" in result[0].text
        assert "vim" in result[0].text
        assert "fake-package" in result[0].text
        
        # Should indicate partial success
        assert "2/3" in result[0].text or "succeeded: 2" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_install_all_invalid_packages_lists_all_failures(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that trying to install multiple non-existent packages lists all of them."""
        # Mock installation failure for multiple packages
        install_error = ExecutionError(
            code="PACKAGE_INSTALL_FAILED",
            message="Package installation failed: Unable to locate packages",
            command="sudo apt-get install -y fake1 fake2 fake3",
            exit_code=100,
            stderr="E: Unable to locate package fake1\nE: Unable to locate package fake2\nE: Unable to locate package fake3",
            details={
                "failed_packages": ["fake1", "fake2", "fake3"]
            }
        )
        package_tools.container.install_packages_use_case.execute.return_value = Result.error(
            install_error
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["fake1", "fake2", "fake3"],
            },
        )

        # Verify all package names are mentioned
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "fake1" in result[0].text
        assert "fake2" in result[0].text
        assert "fake3" in result[0].text

    @pytest.mark.asyncio
    async def test_install_suggests_valid_alternatives_when_available(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that installation errors suggest alternatives when available."""
        # Mock installation failure with suggestions
        install_error = ExecutionError(
            code="PACKAGE_NOT_FOUND_WITH_SUGGESTIONS",
            message="Package not found, but similar packages exist",
            command="sudo apt-get install -y pythn3",
            exit_code=100,
            stderr="E: Unable to locate package pythn3",
            details={
                "suggestions": ["python3", "python3-dev", "python3-pip"],
                "failed_package": "pythn3"
            }
        )
        package_tools.container.install_packages_use_case.execute.return_value = Result.error(
            install_error
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["pythn3"],
            },
        )

        # Verify suggestions are shown
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "pythn3" in result[0].text
        # Should mention available alternatives
        assert "python3" in result[0].text or "similar packages" in result[0].text.lower()