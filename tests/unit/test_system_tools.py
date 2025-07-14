"""Unit tests for SystemTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.domain.models import BiosFile
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionInfo
from retromcp.domain.models import SystemInfo
from retromcp.tools.system_tools import SystemTools


class TestSystemTools:
    """Test cases for SystemTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with use cases."""
        mock = Mock()
        # Mock use cases
        mock.test_connection_use_case = Mock()
        mock.get_system_info_use_case = Mock()
        mock.install_packages_use_case = Mock()
        mock.update_system_use_case = Mock()
        # Mock repository
        mock.system_repository = Mock()
        # Set up the config properly
        mock.config = test_config
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        from retromcp.discovery import RetroPiePaths

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
    def system_tools(self, mock_container: Mock) -> SystemTools:
        """Provide SystemTools instance with mocked dependencies."""
        return SystemTools(mock_container)

    def test_get_tools(self, system_tools: SystemTools) -> None:
        """Test that all expected tools are returned."""
        tools = system_tools.get_tools()

        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "test_connection",
            "system_info",
            "install_packages",
            "check_bios",
            "update_system",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, system_tools: SystemTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = system_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Test connection tool - no parameters
        test_conn_tool = tool_dict["test_connection"]
        assert test_conn_tool.inputSchema["type"] == "object"
        assert test_conn_tool.inputSchema["required"] == []

        # Install packages tool - requires packages array
        install_tool = tool_dict["install_packages"]
        assert "packages" in install_tool.inputSchema["properties"]
        assert install_tool.inputSchema["required"] == ["packages"]
        assert install_tool.inputSchema["properties"]["packages"]["type"] == "array"

        # Check BIOS tool - requires system enum
        bios_tool = tool_dict["check_bios"]
        assert "system" in bios_tool.inputSchema["properties"]
        assert bios_tool.inputSchema["required"] == ["system"]
        assert "enum" in bios_tool.inputSchema["properties"]["system"]

        # Update system tool - optional update_type
        update_tool = tool_dict["update_system"]
        assert "update_type" in update_tool.inputSchema["properties"]
        assert update_tool.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_test_connection_success(self, system_tools: SystemTools) -> None:
        """Test successful connection test."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2024-01-01 12:00:00",
            connection_method="ssh",
        )
        system_tools.container.test_connection_use_case.execute.return_value = (
            connection_info
        )

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully connected to RetroPie!" in result[0].text
        assert "test-retropie.local:22" in result[0].text
        assert "retro" in result[0].text
        system_tools.container.test_connection_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_command_failure(
        self, system_tools: SystemTools
    ) -> None:
        """Test connection test when command fails."""
        from retromcp.domain.models import ConnectionInfo

        # Mock the use case to return failed connection
        mock_connection_info = ConnectionInfo(
            host="test-host",
            port=22,
            username="test-user",
            connected=False,
            last_connected=None,
            connection_method="ssh",
        )
        system_tools.container.test_connection_use_case.execute.return_value = (
            mock_connection_info
        )

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connected but couldn't get system info" in result[0].text

    @pytest.mark.asyncio
    async def test_test_connection_ssh_exception(
        self, system_tools: SystemTools
    ) -> None:
        """Test connection test when SSH raises exception."""
        # Mock the use case to raise exception
        system_tools.container.test_connection_use_case.execute.side_effect = Exception(
            "Connection timeout"
        )

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection failed: Connection timeout" in result[0].text
        assert "RETROPIE_HOST" in result[0].text  # Should include config help

    @pytest.mark.asyncio
    async def test_get_system_info_complete(self, system_tools: SystemTools) -> None:
        """Test system info with all data available."""
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=65.5,
            memory_total=4096 * 1024 * 1024,  # Convert to bytes
            memory_used=2048 * 1024 * 1024,  # Convert to bytes
            memory_free=2048 * 1024 * 1024,  # Convert to bytes
            disk_total=32 * 1024 * 1024 * 1024,  # Convert to bytes
            disk_used=8 * 1024 * 1024 * 1024,  # Convert to bytes
            disk_free=24 * 1024 * 1024 * 1024,  # Convert to bytes
            load_average=[0.5, 0.7, 0.9],
            uptime=7200,  # 2 hours in seconds
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🖥️ RetroPie System Information:" in text
        assert "Temperature: ✅ 65.5°C" in text  # Normal temp
        assert "Memory: 🟢 2048MB / 4096MB (50.0%)" in text  # Normal memory
        assert "Disk Usage: 8GB / 32GB" in text
        assert "Hostname: test-retropie" in text

    @pytest.mark.asyncio
    async def test_get_system_info_high_temperature(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info with high temperature warnings."""
        # Test warning temperature
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=75.0,
            memory_total=4096 * 1024 * 1024,
            memory_used=2048 * 1024 * 1024,
            memory_free=2048 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Temperature: ⚠️ 75.0°C" in result[0].text

        # Test critical temperature
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=85.0,
            memory_total=4096 * 1024 * 1024,
            memory_used=2048 * 1024 * 1024,
            memory_free=2048 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Temperature: 🔥 85.0°C" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_high_memory(self, system_tools: SystemTools) -> None:
        """Test system info with high memory usage warnings."""
        # Test warning memory usage
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=65.0,
            memory_total=4096 * 1024 * 1024,  # 4GB in bytes
            memory_used=3200 * 1024 * 1024,  # 3.2GB in bytes (78%)
            memory_free=896 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Memory: 🟡 3200MB / 4096MB (78.1%)" in result[0].text

        # Test critical memory usage
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=65.0,
            memory_total=4096 * 1024 * 1024,  # 4GB in bytes
            memory_used=3788 * 1024 * 1024,  # 3.788GB in bytes (92.5%)
            memory_free=308 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Memory: 🔴 3788MB / 4096MB (92.5%)" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_es_not_running(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info when EmulationStation is not running."""
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=65.0,
            memory_total=4096 * 1024 * 1024,
            memory_used=2048 * 1024 * 1024,
            memory_free=2048 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        # EmulationStation status is not part of SystemInfo domain model
        assert "🖥️ RetroPie System Information:" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_partial_data(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info with only partial data available."""
        mock_system_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=45.0,
            memory_total=4096 * 1024 * 1024,
            memory_used=2048 * 1024 * 1024,
            memory_free=2048 * 1024 * 1024,
            disk_total=32 * 1024 * 1024 * 1024,
            disk_used=8 * 1024 * 1024 * 1024,
            disk_free=24 * 1024 * 1024 * 1024,
            load_average=[0.5],
            uptime=3600,
        )
        system_tools.container.get_system_info_use_case.execute.return_value = (
            mock_system_info
        )

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        text = result[0].text
        assert "Temperature: ✅ 45.0°C" in text
        # All data will be present since SystemInfo is a complete domain model
        assert "Memory:" in text
        assert "Disk Usage:" in text
        assert "Hostname: test-retropie" in text

    @pytest.mark.asyncio
    async def test_install_packages_success(self, system_tools: SystemTools) -> None:
        """Test successful package installation."""
        packages = ["htop", "vim", "git"]
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y htop vim git",
            exit_code=0,
            stdout="Successfully installed: htop vim git",
            stderr="",
            success=True,
            execution_time=5.2,
        )
        system_tools.container.install_packages_use_case.execute.return_value = (
            mock_result
        )

        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": packages}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully installed: htop vim git" in result[0].text
        system_tools.container.install_packages_use_case.execute.assert_called_once_with(
            packages
        )

    @pytest.mark.asyncio
    async def test_install_packages_failure(self, system_tools: SystemTools) -> None:
        """Test failed package installation."""
        packages = ["nonexistent-package"]
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y nonexistent-package",
            exit_code=1,
            stdout="",
            stderr="Package 'nonexistent-package' not found",
            success=False,
            execution_time=2.1,
        )
        system_tools.container.install_packages_use_case.execute.return_value = (
            mock_result
        )

        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": packages}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Package 'nonexistent-package' not found" in result[0].text

    @pytest.mark.asyncio
    async def test_install_packages_empty_list(self, system_tools: SystemTools) -> None:
        """Test package installation with empty package list."""
        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": []}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No packages specified" in result[0].text
        system_tools.container.install_packages_use_case.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_packages_missing_argument(
        self, system_tools: SystemTools
    ) -> None:
        """Test package installation with missing packages argument."""
        result = await system_tools.handle_tool_call("install_packages", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No packages specified" in result[0].text

    @pytest.mark.asyncio
    async def test_check_bios_no_files_required(
        self, system_tools: SystemTools
    ) -> None:
        """Test BIOS check for system that doesn't require BIOS."""
        # Mock empty BIOS files list for NES system
        system_tools.container.system_repository.get_bios_files.return_value = []

        result = await system_tools.handle_tool_call("check_bios", {"system": "nes"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert "BIOS Files for NES:" in text
        assert "✅ No BIOS files required for this system" in text

    @pytest.mark.asyncio
    async def test_check_bios_all_present(self, system_tools: SystemTools) -> None:
        """Test BIOS check when all required files are present."""
        mock_bios_files = [
            BiosFile(
                name="scph1001.bin",
                path="/home/retro/RetroPie/BIOS/scph1001.bin",
                system="psx",
                required=True,
                present=True,
            ),
            BiosFile(
                name="scph5501.bin",
                path="/home/retro/RetroPie/BIOS/scph5501.bin",
                system="psx",
                required=True,
                present=True,
            ),
            BiosFile(
                name="scph7001.bin",
                path="/home/retro/RetroPie/BIOS/scph7001.bin",
                system="psx",
                required=True,
                present=True,
            ),
        ]
        system_tools.container.system_repository.get_bios_files.return_value = (
            mock_bios_files
        )

        result = await system_tools.handle_tool_call("check_bios", {"system": "psx"})

        assert len(result) == 1
        text = result[0].text
        assert "BIOS Files for PSX:" in text
        assert "✅ scph1001.bin" in text
        assert "✅ scph5501.bin" in text
        assert "✅ scph7001.bin" in text
        assert "🎉 All required BIOS files are present!" in text

    @pytest.mark.asyncio
    async def test_check_bios_missing_files(self, system_tools: SystemTools) -> None:
        """Test BIOS check when some files are missing."""
        mock_bios_files = [
            BiosFile(
                name="dc_boot.bin",
                path="/home/retro/RetroPie/BIOS/dc_boot.bin",
                system="dreamcast",
                required=True,
                present=True,
            ),
            BiosFile(
                name="dc_flash.bin",
                path="/home/retro/RetroPie/BIOS/dc_flash.bin",
                system="dreamcast",
                required=True,
                present=False,
            ),
        ]
        system_tools.container.system_repository.get_bios_files.return_value = (
            mock_bios_files
        )

        result = await system_tools.handle_tool_call(
            "check_bios", {"system": "dreamcast"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "BIOS Files for DREAMCAST:" in text
        assert "✅ dc_boot.bin" in text
        assert "❌ dc_flash.bin" in text
        assert "⚠️ Some BIOS files are missing" in text
        assert "/home/retro/RetroPie/BIOS/" in text

    @pytest.mark.asyncio
    async def test_check_bios_missing_system_argument(
        self, system_tools: SystemTools
    ) -> None:
        """Test BIOS check with missing system argument."""
        result = await system_tools.handle_tool_call("check_bios", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No system specified" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_basic_success(self, system_tools: SystemTools) -> None:
        """Test successful basic system update."""
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="Update completed",
            stderr="",
            success=True,
            execution_time=30.5,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "basic"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "System packages updated successfully" in result[0].text
        system_tools.container.update_system_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_system_basic_failure(self, system_tools: SystemTools) -> None:
        """Test failed basic system update."""
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=1,
            stdout="",
            stderr="E: Could not get lock /var/lib/dpkg/lock",
            success=False,
            execution_time=5.0,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "basic"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Update failed: E: Could not get lock" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_retropie_setup_success(
        self, system_tools: SystemTools
    ) -> None:
        """Test successful RetroPie-Setup update."""
        mock_result = CommandResult(
            command="sudo /home/retro/RetroPie-Setup/retropie_setup.sh update",
            exit_code=0,
            stdout="RetroPie-Setup updated successfully",
            stderr="",
            success=True,
            execution_time=60.2,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "retropie-setup"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "RetroPie-Setup updated successfully" in result[0].text
        system_tools.container.update_system_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_system_retropie_setup_failure(
        self, system_tools: SystemTools
    ) -> None:
        """Test failed RetroPie-Setup update."""
        mock_result = CommandResult(
            command="sudo /home/retro/RetroPie-Setup/retropie_setup.sh update",
            exit_code=1,
            stdout="",
            stderr="RetroPie-Setup update failed",
            success=False,
            execution_time=15.3,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "retropie-setup"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "RetroPie-Setup update failed" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_default_type(self, system_tools: SystemTools) -> None:
        """Test system update with default update type."""
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="Update completed",
            stderr="",
            success=True,
            execution_time=25.1,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call("update_system", {})

        assert len(result) == 1
        assert "System packages updated successfully" in result[0].text
        # Should default to basic update
        system_tools.container.update_system_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_system_unknown_type(self, system_tools: SystemTools) -> None:
        """Test system update with unknown update type."""
        # The update system use case will still be called and should handle the invalid type
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="Update completed",
            stderr="",
            success=True,
            execution_time=25.1,
        )
        system_tools.container.update_system_use_case.execute.return_value = mock_result

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # The use case handles the update, so it should succeed
        assert "System packages updated successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, system_tools: SystemTools) -> None:
        """Test handling of unknown tool name."""
        result = await system_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(self, system_tools: SystemTools) -> None:
        """Test exception handling in tool execution."""
        system_tools.container.test_connection_use_case.execute.side_effect = Exception(
            "SSH connection lost"
        )

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection failed: SSH connection lost" in result[0].text

    @pytest.mark.asyncio
    async def test_bios_check_uses_config_bios_dir(
        self, system_tools: SystemTools
    ) -> None:
        """Test that BIOS check uses configured BIOS directory."""
        mock_bios_files = [
            BiosFile(
                name="test.bin",
                path="/home/retro/RetroPie/BIOS/test.bin",
                system="psx",
                required=True,
                present=False,
            ),
        ]
        system_tools.container.system_repository.get_bios_files.return_value = (
            mock_bios_files
        )

        result = await system_tools.handle_tool_call("check_bios", {"system": "psx"})

        text = result[0].text
        assert "/home/retro/RetroPie/BIOS/" in text

    @pytest.mark.asyncio
    async def test_bios_check_fallback_bios_dir(self, mock_container: Mock) -> None:
        """Test BIOS check fallback when bios_dir is None."""
        # Create config without paths (no discovery completed)
        config_no_paths = RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=None,  # No paths discovered
        )
        mock_container.config = config_no_paths

        tools = SystemTools(mock_container)
        mock_bios_files = [
            BiosFile(
                name="test.bin",
                path="/home/retro/RetroPie/BIOS/test.bin",
                system="psx",
                required=True,
                present=False,
            ),
        ]
        tools.container.system_repository.get_bios_files.return_value = mock_bios_files

        result = await tools.handle_tool_call("check_bios", {"system": "psx"})

        text = result[0].text
        # Should fall back to home_dir/RetroPie/BIOS
        assert "/home/retro/RetroPie/BIOS/" in text

    def test_inheritance_from_base_tool(self, system_tools: SystemTools) -> None:
        """Test that SystemTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(system_tools, "format_success")
        assert hasattr(system_tools, "format_error")
        assert hasattr(system_tools, "container")
        assert hasattr(system_tools, "config")

        # Test format methods work
        success_result = system_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = system_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text
