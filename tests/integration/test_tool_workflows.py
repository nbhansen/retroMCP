"""Integration tests for complete tool workflows.

Tests the full flow: Tool call → SSH Handler → Repository → Command execution
Also verifies CLAUDE.md compliance during tool execution workflows.
"""

from dataclasses import is_dataclass
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.ssh_handler import RetroPieSSH
from retromcp.tools.gaming_system_tools import GamingSystemTools
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools
from retromcp.tools.system_management_tools import SystemManagementTools


class TestSystemManagementToolsWorkflow:
    """Test complete system management tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration with paths."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def system_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> SystemManagementTools:
        """Create SystemManagementTools instance with mocked dependencies."""
        from retromcp.container import Container

        mock_container = Mock(spec=Container)
        mock_container.retropie_client = mock_ssh_handler
        mock_container.config = test_config
        return SystemManagementTools(mock_container)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify that an object follows CLAUDE.md principles."""
        # Test immutability for dataclasses
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True, (
                f"{obj.__class__.__name__} should be frozen for immutability"
            )

        # Test meaningful naming
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4, f"Class name '{class_name}' too short"
        assert class_name[0].isupper(), (
            f"Class name '{class_name}' should use PascalCase"
        )

    @pytest.mark.asyncio
    async def test_get_system_info_workflow(
        self,
        system_tools: SystemManagementTools,
        mock_ssh_handler: Mock,  # noqa: ARG002
        test_config: RetroPieConfig,
    ) -> None:
        """Test complete system_info workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check for config
        self._verify_claude_md_compliance(test_config)

        # Mock the get_system_info use case that the tool actually calls
        mock_system_info = Mock()
        mock_system_info.hostname = "test-retropie"
        mock_system_info.cpu_temperature = 55.4
        mock_system_info.load_average = "0.25, 0.30, 0.35"
        mock_system_info.uptime = "2 days"
        mock_system_info.memory_total = 1024 * 1024 * 1024  # 1GB in bytes
        mock_system_info.memory_used = 512 * 1024 * 1024  # 512MB in bytes
        mock_system_info.memory_free = 512 * 1024 * 1024  # 512MB in bytes
        mock_system_info.disk_total = 32 * 1024 * 1024 * 1024  # 32GB in bytes
        mock_system_info.disk_used = 12 * 1024 * 1024 * 1024  # 12GB in bytes
        mock_system_info.disk_free = 20 * 1024 * 1024 * 1024  # 20GB in bytes

        mock_use_case = Mock()
        mock_use_case.execute.return_value = mock_system_info
        system_tools.container.get_system_info_use_case = mock_use_case

        # Execute the tool workflow
        result = await system_tools.handle_tool_call(
            "get_system_info", {"category": "all"}
        )

        # Verify the workflow completed successfully and follows MCP protocol
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"

        response = result[0]
        assert hasattr(response, "text"), (
            "Response should have text attribute for MCP compliance"
        )

        # Verify system information is collected
        response_text = response.text
        assert "55.4°C" in response_text or "temperature" in response_text.lower()
        assert "memory" in response_text.lower() or "512" in response_text
        assert (
            "disk" in response_text.lower()
            or "32" in response_text
            or "storage" in response_text.lower()
        )

        # Verify use case was called
        mock_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_packages_workflow(
        self,
        system_tools: SystemManagementTools,
        mock_ssh_handler: Mock,  # noqa: ARG002
        test_config: RetroPieConfig,
    ) -> None:
        """Test complete install_packages workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock the install_packages use case that the tool actually calls
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "Successfully installed htop, vim"
        mock_result.stderr = ""

        mock_use_case = Mock()
        mock_use_case.execute.return_value = mock_result
        system_tools.container.install_packages_use_case = mock_use_case

        # Execute the tool workflow
        result = await system_tools.handle_tool_call(
            "manage_package",
            {"action": "install", "packages": ["htop", "vim"]},
        )

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"

        response = result[0]
        assert hasattr(response, "text"), "Response should have text attribute"

        # Verify package installation was attempted
        response_text = response.text
        assert "htop" in response_text or "package" in response_text.lower()
        assert "✅" in response_text or "success" in response_text.lower()

        # Verify use case was called
        mock_use_case.execute.assert_called_once_with(["htop", "vim"])

    @pytest.mark.asyncio
    async def test_error_propagation_workflow(
        self,
        system_tools: SystemManagementTools,
        mock_ssh_handler: Mock,  # noqa: ARG002
        test_config: RetroPieConfig,
    ) -> None:
        """Test error handling and propagation workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock use case that will fail
        mock_use_case = Mock()
        mock_use_case.execute.side_effect = Exception("Command failed")
        system_tools.container.get_system_info_use_case = mock_use_case

        # Execute tool that will fail
        result = await system_tools.handle_tool_call(
            "get_system_info", {"category": "all"}
        )

        # Verify error handling follows MCP protocol
        assert isinstance(result, list), (
            "Error response should still be list for MCP compliance"
        )
        assert len(result) > 0, "Error response should have content"

        response = result[0]
        assert hasattr(response, "text"), "Error response should have text attribute"

        # Verify error is communicated properly
        response_text = response.text.lower()
        assert any(word in response_text for word in ["error", "failed", "unable"]), (
            "Error response should indicate failure"
        )


class TestHardwareMonitoringToolsWorkflow:
    """Test hardware tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def hardware_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> HardwareMonitoringTools:
        """Create HardwareMonitoringTools instance."""
        from retromcp.container import Container

        mock_container = Mock(spec=Container)
        mock_container.retropie_client = mock_ssh_handler
        mock_container.config = test_config
        return HardwareMonitoringTools(mock_container)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True

        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_check_temperature_workflow(
        self,
        hardware_tools: HardwareMonitoringTools,
        mock_ssh_handler: Mock,
        test_config: RetroPieConfig,
    ) -> None:
        """Test temperature check workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock temperature commands
        mock_result1 = Mock()
        mock_result1.success = True
        mock_result1.stdout = "temp=55.4'C"
        mock_result1.stderr = ""

        mock_result2 = Mock()
        mock_result2.success = True
        mock_result2.stdout = "throttled=0x0"
        mock_result2.stderr = ""

        mock_ssh_handler.execute_command.side_effect = [mock_result1, mock_result2]

        # Execute the tool workflow
        result = await hardware_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"

        response = result[0]
        assert hasattr(response, "text"), "Response should have text for MCP compliance"

        # Verify temperature information
        response_text = response.text
        assert "55" in response_text or "temperature" in response_text.lower()


class TestGamingSystemToolsWorkflow:
    """Test gaming system tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            bios_dir="/home/retro/RetroPie/BIOS",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def gaming_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> GamingSystemTools:
        """Create GamingSystemTools instance."""
        from retromcp.container import Container

        mock_container = Mock(spec=Container)
        mock_container.retropie_client = mock_ssh_handler
        mock_container.config = test_config
        return GamingSystemTools(mock_container)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True

        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_check_bios_workflow(
        self,
        gaming_tools: GamingSystemTools,
        mock_ssh_handler: Mock,
        test_config: RetroPieConfig,
    ) -> None:
        """Test BIOS checking workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock BIOS directory listing
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "gba_bios.bin\ndc_bios.bin\nps1_bios.bin"
        mock_result.stderr = ""

        mock_ssh_handler.execute_command.return_value = mock_result

        # Execute the tool workflow
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "emulator", "action": "configure", "target": "bios"},
        )

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"

        response = result[0]
        assert hasattr(response, "text"), "Response should have text for MCP compliance"

        # Verify BIOS information
        response_text = response.text
        assert "bios" in response_text.lower() or "gba" in response_text


class TestCrossComponentWorkflow:
    """Test workflows that span multiple components with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True

        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_discovery_and_configuration_workflow(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test complete discovery to configuration workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock the complete workflow
        with patch("retromcp.ssh_handler.RetroPieSSH") as mock_ssh_class:
            mock_ssh = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.stdout = "retropie-test"
            mock_result.stderr = ""
            mock_ssh.execute_command = Mock(return_value=mock_result)
            mock_ssh_class.return_value = mock_ssh

            # Create tools with mocked SSH
            from retromcp.container import Container

            mock_container = Mock(spec=Container)
            mock_container.retropie_client = mock_ssh
            mock_container.config = test_config
            system_tools = SystemManagementTools(mock_container)

            # CLAUDE.md compliance check for tools
            self._verify_claude_md_compliance(test_config)

            # Mock the connection use case
            mock_connection_info = Mock()
            mock_connection_info.connected = True
            mock_connection_info.host = "test-retropie.local"
            mock_connection_info.port = 22
            mock_connection_info.username = "retro"

            mock_use_case = Mock()
            mock_use_case.execute.return_value = mock_connection_info
            mock_container.test_connection_use_case = mock_use_case

            # Test a simple tool execution to verify the workflow
            result = await system_tools.handle_tool_call(
                "manage_connection", {"action": "test"}
            )

            # Verify MCP compliance
            assert isinstance(result, list), "Workflow should return MCP-compliant list"
            assert len(result) > 0, "Workflow should return content"

            # Verify tool follows MCP protocol
            response = result[0]
            assert hasattr(response, "text"), "Response should be MCP TextContent"

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_config: RetroPieConfig) -> None:
        """Test error recovery across components with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock error scenario followed by recovery
        with patch("retromcp.ssh_handler.RetroPieSSH") as mock_ssh_class:
            mock_ssh = Mock()
            # First call fails, second succeeds
            mock_result_fail = Mock()
            mock_result_fail.success = False
            mock_result_fail.stdout = ""
            mock_result_fail.stderr = "Connection failed"

            mock_result_success = Mock()
            mock_result_success.success = True
            mock_result_success.stdout = "retropie-test"
            mock_result_success.stderr = ""

            mock_ssh.execute_command = Mock(
                side_effect=[
                    mock_result_fail,  # First call fails
                    mock_result_success,  # Second call succeeds
                ]
            )
            mock_ssh_class.return_value = mock_ssh

            from retromcp.container import Container

            mock_container = Mock(spec=Container)
            mock_container.retropie_client = mock_ssh
            mock_container.config = test_config

            # Mock the connection use case - first fails, then succeeds
            mock_connection_info_fail = Mock()
            mock_connection_info_fail.connected = False
            mock_connection_info_fail.host = "test-retropie.local"
            mock_connection_info_fail.port = 22
            mock_connection_info_fail.username = "retro"

            mock_connection_info_success = Mock()
            mock_connection_info_success.connected = True
            mock_connection_info_success.host = "test-retropie.local"
            mock_connection_info_success.port = 22
            mock_connection_info_success.username = "retro"

            mock_use_case = Mock()
            mock_use_case.execute.side_effect = [
                mock_connection_info_fail,
                mock_connection_info_success,
            ]
            mock_container.test_connection_use_case = mock_use_case

            system_tools = SystemManagementTools(mock_container)

            # First tool call should handle error gracefully
            result1 = await system_tools.handle_tool_call(
                "manage_connection", {"action": "test"}
            )
            assert isinstance(result1, list), (
                "Error handling should return MCP-compliant list"
            )
            assert len(result1) > 0, "Error handling should return content"

            # Second tool call should succeed
            result2 = await system_tools.handle_tool_call(
                "manage_connection", {"action": "test"}
            )
            assert isinstance(result2, list), (
                "Recovery should return MCP-compliant list"
            )
            assert len(result2) > 0, "Recovery should return content"

            # Verify both use case calls were made
            assert mock_use_case.execute.call_count == 2
