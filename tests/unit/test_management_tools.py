"""Unit tests for ManagementTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.management_tools import ManagementTools


class TestManagementTools:
    """Test cases for ManagementTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config
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
    def management_tools(self, mock_container: Mock) -> ManagementTools:
        """Provide ManagementTools instance with mocked dependencies."""
        return ManagementTools(mock_container)

    def test_get_tools(self, management_tools: ManagementTools) -> None:
        """Test that all expected tools are returned."""
        tools = management_tools.get_tools()

        # Should have all management tools
        assert len(tools) >= 3
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "manage_services",
            "manage_packages",
            "manage_files",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_manage_services_tool_schema(
        self, management_tools: ManagementTools
    ) -> None:
        """Test that manage_services tool schema is properly defined."""
        tools = management_tools.get_tools()
        service_tool = next(t for t in tools if t.name == "manage_services")

        # Check schema structure
        assert service_tool.inputSchema["type"] == "object"
        assert "action" in service_tool.inputSchema["properties"]
        assert "service" in service_tool.inputSchema["properties"]

        # Check action enum values
        actions = service_tool.inputSchema["properties"]["action"]["enum"]
        expected_actions = ["start", "stop", "restart", "enable", "disable", "status"]
        for action in expected_actions:
            assert action in actions

        # Check required fields
        assert service_tool.inputSchema["required"] == ["action", "service"]

    @pytest.mark.asyncio
    async def test_manage_services_start_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful service start."""
        # Mock successful service start
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("sudo systemctl start pigpiod", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "start", "service": "pigpiod"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "pigpiod" in result[0].text
        assert "started" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_stop_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful service stop."""
        # Mock successful service stop
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("sudo systemctl stop emulationstation", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "stop", "service": "emulationstation"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "emulationstation" in result[0].text
        assert "stopped" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_restart_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful service restart."""
        # Mock successful service restart
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("sudo systemctl restart pi5-fancontrol", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "restart", "service": "pi5-fancontrol"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "pi5-fancontrol" in result[0].text
        assert "restarted" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_enable_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful service enable."""
        # Mock successful service enable
        management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "sudo systemctl enable pigpiod",
            0,
            "Created symlink /etc/systemd/system/multi-user.target.wants/pigpiod.service",
            "",
            True,
            0.1,
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "enable", "service": "pigpiod"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "pigpiod" in result[0].text
        assert "enabled" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_disable_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful service disable."""
        # Mock successful service disable
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "sudo systemctl disable pigpiod",
                0,
                "Removed /etc/systemd/system/multi-user.target.wants/pigpiod.service",
                "",
                True,
                0.1,
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "disable", "service": "pigpiod"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "pigpiod" in result[0].text
        assert "disabled" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_status(
        self, management_tools: ManagementTools
    ) -> None:
        """Test service status check."""
        # Mock service status output
        status_output = """● pigpiod.service - Daemon for pigpio library
     Loaded: loaded (/lib/systemd/system/pigpiod.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-01-13 14:30:00 UTC; 1h ago
   Main PID: 1234 (pigpiod)
      Tasks: 1 (limit: 9345)
     Memory: 1.2M
        CPU: 100ms
     CGroup: /system.slice/pigpiod.service
             └─1234 /usr/bin/pigpiod -l"""

        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "systemctl status pigpiod --no-pager", 0, status_output, "", True, 0.1
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "status", "service": "pigpiod"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "pigpiod.service" in result[0].text
        assert "active (running)" in result[0].text
        assert "enabled" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_services_status_inactive(
        self, management_tools: ManagementTools
    ) -> None:
        """Test inactive service status."""
        # Mock inactive service
        status_output = """● pi5-fancontrol.service - Raspberry Pi 5 Fan Control
     Loaded: loaded (/etc/systemd/system/pi5-fancontrol.service; disabled; vendor preset: enabled)
     Active: inactive (dead)"""

        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "systemctl status pi5-fancontrol --no-pager",
                3,  # Exit code 3 for inactive service
                status_output,
                "",
                False,
                0.1,
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "status", "service": "pi5-fancontrol"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "pi5-fancontrol.service" in result[0].text
        assert "inactive (dead)" in result[0].text
        assert "disabled" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_services_failure(
        self, management_tools: ManagementTools
    ) -> None:
        """Test service operation failure."""
        # Mock failed service start
        management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "sudo systemctl start nonexistent",
            1,
            "",
            "Failed to start nonexistent.service: Unit nonexistent.service not found.",
            False,
            0.1,
        )

        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "start", "service": "nonexistent"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "nonexistent" in result[0].text
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_invalid_action(
        self, management_tools: ManagementTools
    ) -> None:
        """Test invalid action handling."""
        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "invalid", "service": "pigpiod"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_services_missing_service(
        self, management_tools: ManagementTools
    ) -> None:
        """Test missing service parameter."""
        result = await management_tools.handle_tool_call(
            "manage_services", {"action": "start"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "service name required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, management_tools: ManagementTools) -> None:
        """Test handling of unknown tool name."""
        result = await management_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Unknown tool" in result[0].text

    def test_inheritance_from_base_tool(
        self, management_tools: ManagementTools
    ) -> None:
        """Test that ManagementTools properly inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(management_tools, BaseTool)
        assert hasattr(management_tools, "container")
        assert hasattr(management_tools, "config")
        assert hasattr(management_tools, "format_error")
        assert hasattr(management_tools, "format_success")
        assert hasattr(management_tools, "format_warning")
        assert hasattr(management_tools, "format_info")

    # Package Management Tests
    def test_manage_packages_tool_schema(
        self, management_tools: ManagementTools
    ) -> None:
        """Test that manage_packages tool schema is properly defined."""
        tools = management_tools.get_tools()
        package_tool = next(t for t in tools if t.name == "manage_packages")

        # Check schema structure
        assert package_tool.inputSchema["type"] == "object"
        assert "action" in package_tool.inputSchema["properties"]
        assert "packages" in package_tool.inputSchema["properties"]

        # Check action enum values
        actions = package_tool.inputSchema["properties"]["action"]["enum"]
        expected_actions = ["install", "remove", "update", "search", "list"]
        for action in expected_actions:
            assert action in actions

        # Check required fields
        assert package_tool.inputSchema["required"] == ["action"]

    @pytest.mark.asyncio
    async def test_manage_packages_install_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful package installation."""
        # Mock successful package install
        management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "sudo apt-get install -y wiringpi",
            0,
            "Reading package lists...\nBuilding dependency tree...\nwiringpi is already the newest version.\n",
            "",
            True,
            2.5,
        )

        result = await management_tools.handle_tool_call(
            "manage_packages", {"action": "install", "packages": ["wiringpi"]}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "wiringpi" in result[0].text
        assert "installed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_packages_remove_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful package removal."""
        # Mock successful package removal
        management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "sudo apt-get remove -y some-package",
            0,
            "Reading package lists...\nRemoving some-package...\nProcessing triggers...\n",
            "",
            True,
            1.8,
        )

        result = await management_tools.handle_tool_call(
            "manage_packages", {"action": "remove", "packages": ["some-package"]}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "some-package" in result[0].text
        assert "removed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_packages_update_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful package update."""
        # Mock successful package update
        management_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sudo apt-get update",
                0,
                "Get:1 http://archive.ubuntu.com...",
                "",
                True,
                5.2,
            ),
            CommandResult(
                "sudo apt-get upgrade -y",
                0,
                "Reading package lists...\n0 upgraded, 0 newly installed",
                "",
                True,
                3.1,
            ),
        ]

        result = await management_tools.handle_tool_call(
            "manage_packages", {"action": "update"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "updated" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_packages_search_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful package search."""
        # Mock successful package search
        search_output = """pigpio/stable 1.79-1+deb11u1 armhf
  Library for Raspberry Pi GPIO control

pigpio-tools/stable 1.79-1+deb11u1 armhf
  Client tools for Raspberry Pi GPIO control"""

        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("apt-cache search pigpio", 0, search_output, "", True, 0.8)
        )

        result = await management_tools.handle_tool_call(
            "manage_packages", {"action": "search", "packages": ["pigpio"]}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "pigpio" in result[0].text
        assert "Library for Raspberry Pi GPIO control" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_packages_list_installed(
        self, management_tools: ManagementTools
    ) -> None:
        """Test listing installed packages."""
        # Mock installed packages list
        list_output = """ii  pigpio          1.79-1+deb11u1  armhf   Library for Raspberry Pi GPIO control
ii  wiringpi        2.60            armhf   GPIO Interface library for the Raspberry Pi"""

        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("dpkg -l | grep '^ii'", 0, list_output, "", True, 0.5)
        )

        result = await management_tools.handle_tool_call(
            "manage_packages", {"action": "list"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "pigpio" in result[0].text
        assert "wiringpi" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_packages_failure(
        self, management_tools: ManagementTools
    ) -> None:
        """Test package operation failure."""
        # Mock failed package install
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "sudo apt-get install -y nonexistent-package",
                100,
                "",
                "E: Unable to locate package nonexistent-package",
                False,
                1.2,
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_packages",
            {"action": "install", "packages": ["nonexistent-package"]},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Unable to locate package" in result[0].text

    # File Management Tests
    def test_manage_files_tool_schema(self, management_tools: ManagementTools) -> None:
        """Test that manage_files tool schema is properly defined."""
        tools = management_tools.get_tools()
        file_tool = next(t for t in tools if t.name == "manage_files")

        # Check schema structure
        assert file_tool.inputSchema["type"] == "object"
        assert "action" in file_tool.inputSchema["properties"]
        assert "path" in file_tool.inputSchema["properties"]

        # Check action enum values
        actions = file_tool.inputSchema["properties"]["action"]["enum"]
        expected_actions = [
            "list",
            "create",
            "delete",
            "copy",
            "move",
            "permissions",
            "backup",
        ]
        for action in expected_actions:
            assert action in actions

        # Check required fields
        assert file_tool.inputSchema["required"] == ["action", "path"]

    @pytest.mark.asyncio
    async def test_manage_files_list_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful file listing."""
        # Mock successful directory listing
        list_output = """total 12
drwxr-xr-x 2 retro retro 4096 Jan 13 14:30 BIOS
drwxr-xr-x 5 retro retro 4096 Jan 13 14:31 roms
-rw-r--r-- 1 retro retro  123 Jan 13 14:32 config.txt"""

        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("ls -la /home/retro/RetroPie", 0, list_output, "", True, 0.3)
        )

        result = await management_tools.handle_tool_call(
            "manage_files", {"action": "list", "path": "/home/retro/RetroPie"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "BIOS" in result[0].text
        assert "roms" in result[0].text
        assert "config.txt" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_files_create_directory_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful directory creation."""
        # Mock successful directory creation
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("mkdir -p /home/retro/custom-roms", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_files",
            {
                "action": "create",
                "path": "/home/retro/custom-roms",
                "type": "directory",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "created" in result[0].text.lower()
        assert "/home/retro/custom-roms" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_files_delete_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful file deletion."""
        # Mock successful file deletion
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("rm -rf /tmp/test-file.txt", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_files", {"action": "delete", "path": "/home/retro/test-file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "deleted" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_files_copy_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful file copy."""
        # Mock successful file copy
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "cp /home/retro/source.txt /home/retro/backup.txt", 0, "", "", True, 0.2
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_files",
            {
                "action": "copy",
                "path": "/home/retro/source.txt",
                "destination": "/home/retro/backup.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "copied" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_files_permissions_success(
        self, management_tools: ManagementTools
    ) -> None:
        """Test successful permission change."""
        # Mock successful permission change
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult("chmod 755 /home/retro/script.sh", 0, "", "", True, 0.1)
        )

        result = await management_tools.handle_tool_call(
            "manage_files",
            {"action": "permissions", "path": "/home/retro/script.sh", "mode": "755"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "permissions" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_files_failure(
        self, management_tools: ManagementTools
    ) -> None:
        """Test file operation failure."""
        # Mock failed file operation
        management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                "ls /nonexistent/path",
                2,
                "",
                "ls: cannot access '/nonexistent/path': No such file or directory",
                False,
                0.1,
            )
        )

        result = await management_tools.handle_tool_call(
            "manage_files", {"action": "list", "path": "/nonexistent/path"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "No such file or directory" in result[0].text
