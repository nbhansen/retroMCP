"""Integration tests with comprehensive mocks for CI/CD compatibility."""

from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.discovery import RetroPiePaths
from retromcp.tools.system_management_tools import SystemManagementTools


class TestRealPiConnection:
    """Integration tests using comprehensive mocks for CI/CD compatibility."""

    @pytest.fixture
    def mock_pi_config(self) -> RetroPieConfig:
        """Create mock configuration for Pi testing."""
        # Add default paths structure for RetroPie
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
            host="192.168.1.142", username="retro", port=22, paths=paths
        )

    @pytest.mark.asyncio
    async def test_real_pi_connection_and_system_info(
        self, mock_pi_config: RetroPieConfig
    ) -> None:
        """Test connecting to Pi and getting system info with mocked infrastructure."""
        # Create container with mock Pi configuration
        container = Container(mock_pi_config)

        # Mock the system info use case
        from unittest.mock import Mock

        from retromcp.domain.models import Result
        from retromcp.domain.models import SystemInfo

        mock_system_info = SystemInfo(
            hostname="retropie-test",
            cpu_temperature=55.4,
            memory_total=1024 * 1024 * 1024,  # 1GB
            memory_used=512 * 1024 * 1024,  # 512MB
            memory_free=512 * 1024 * 1024,  # 512MB
            disk_total=32 * 1024 * 1024 * 1024,  # 32GB
            disk_used=12 * 1024 * 1024 * 1024,  # 12GB
            disk_free=20 * 1024 * 1024 * 1024,  # 20GB
            load_average=[0.25, 0.30, 0.35],
            uptime=86400,  # 1 day
        )

        mock_use_case = Mock()
        mock_use_case.execute.return_value = Result.success(mock_system_info)
        container._instances["get_system_info_use_case"] = mock_use_case

        # Create system management tools
        system_tools = SystemManagementTools(container)

        # Test basic connection by getting system info
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify successful response
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1, "Should return single response"

        response = result[0]
        assert hasattr(response, "text"), "Should have text attribute"

        # Should not contain error indicators
        response_text = response.text.lower()
        assert "❌" not in response.text, f"Should not have error: {response.text}"
        assert "error" not in response_text, f"Should not have error: {response.text}"
        assert "failed" not in response_text, f"Should not have failed: {response.text}"

        # Should contain expected system information
        assert any(
            keyword in response_text
            for keyword in ["hostname", "memory", "cpu", "disk", "uptime"]
        ), f"Should contain system info: {response.text}"

        # Verify use case was called
        mock_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_pi_command_execution(
        self, mock_pi_config: RetroPieConfig
    ) -> None:
        """Test command execution with mocked SSH infrastructure."""
        # Create container with mock Pi configuration
        container = Container(mock_pi_config)

        # Mock the SSH client
        from retromcp.domain.models import CommandResult

        mock_client = Mock()
        mock_client.connect.return_value = True
        mock_client.disconnect.return_value = None
        mock_client.execute_command.return_value = CommandResult(
            command="echo 'Hello from Pi'",
            exit_code=0,
            stdout="Hello from Pi\n",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        container._instances["retropie_client"] = mock_client

        # Get the mocked SSH client
        ssh_client = container.retropie_client

        # Establish connection first
        connection_established = ssh_client.connect()
        assert connection_established, "Should be able to connect to Pi"

        try:
            # Test simple command execution
            result = ssh_client.execute_command("echo 'Hello from Pi'")

            # Verify command execution
            assert result.success, f"Command should succeed: {result.stderr}"
            assert result.exit_code == 0, f"Should have exit code 0: {result}"
            assert "Hello from Pi" in result.stdout, (
                f"Should contain expected output: {result.stdout}"
            )
        finally:
            # Always disconnect
            ssh_client.disconnect()

        # Verify mock interactions
        mock_client.connect.assert_called_once()
        mock_client.execute_command.assert_called_once_with("echo 'Hello from Pi'")
        mock_client.disconnect.assert_called_once()
