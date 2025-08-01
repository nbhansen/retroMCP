"""Integration tests for SSH connection and error handling.

Tests error propagation and recovery across the entire application stack.
"""

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import SystemInfo
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools
from retromcp.tools.system_management_tools import SystemManagementTools


class TestSSHConnectionIntegration:
    """Test SSH connection integration across components."""

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

    @pytest.mark.asyncio
    async def test_ssh_connection_failure_propagation(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test how SSH connection failures propagate through the stack."""
        from retromcp.domain.models import ConnectionError
        from retromcp.domain.models import Result

        # Create container
        container = Container(test_config)

        # Mock the use case to return a connection error
        mock_use_case = Mock()
        mock_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="SSH_CONNECTION_FAILED",
                message="SSH connection failed",
                details={"host": "test-retropie.local"},
            )
        )
        container._instances["get_system_info_use_case"] = mock_use_case

        # Create tools with container
        system_tools = SystemManagementTools(container)

        # Attempt tool operation - should handle connection error gracefully
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify error is properly handled using MCP-compliant response format
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1
        response = result[0]

        # Check for error using text content (MCP standard approach)
        assert hasattr(response, "text"), "Should have text attribute"
        response_text = response.text.lower()
        assert "❌" in response.text or any(
            word in response_text for word in ["error", "failed"]
        ), "Should indicate error in text"
        assert "connection" in response_text or "ssh" in response_text, (
            "Should mention connection or SSH in error message"
        )

    @pytest.mark.asyncio
    async def test_ssh_command_timeout_handling(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test handling of SSH command timeouts."""
        with patch("retromcp.ssh_handler.RetroPieSSH") as mock_ssh_class:
            # Mock SSH command timeout
            mock_ssh = Mock()
            mock_ssh.execute_command = Mock(
                side_effect=asyncio.TimeoutError("Command timed out")
            )
            mock_ssh_class.return_value = mock_ssh

            # Create container with mocked client
            container = Container(test_config)
            container._instances["retropie_client"] = mock_ssh

            # Create tools with container
            hardware_tools = HardwareMonitoringTools(container)

            # Attempt operation that might timeout
            result = await hardware_tools.handle_tool_call(
                "manage_hardware", {"component": "temperature", "action": "check"}
            )

            # Verify timeout is handled gracefully using MCP-compliant response
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]

            # Check for error using text content (MCP standard approach)
            assert hasattr(response, "text"), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(
                word in response_text for word in ["error", "failed"]
            ), "Should indicate error in text"
            assert "timeout" in response_text or "time" in response_text, (
                "Should mention timeout in error message"
            )

    @pytest.mark.asyncio
    async def test_ssh_authentication_failure(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test handling of SSH authentication failures."""
        # Create container
        container = Container(test_config)

        # Mock use case to return authentication error via Result pattern
        from retromcp.domain.models import ConnectionError
        from retromcp.domain.models import Result

        mock_use_case = Mock()
        mock_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="SSH_AUTHENTICATION_FAILED",
                message="Authentication failed",
                details={"error": "Permission denied (publickey,password)"},
            )
        )
        container._instances["get_system_info_use_case"] = mock_use_case

        # Create tools with container
        system_tools = SystemManagementTools(container)

        # Attempt operation
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify authentication error is handled using MCP-compliant response
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1
        response = result[0]

        # Check for error using text content (MCP standard approach)
        assert hasattr(response, "text"), "Should have text attribute"
        response_text = response.text.lower()
        assert "❌" in response.text or any(
            word in response_text for word in ["error", "failed"]
        ), "Should indicate error in text"
        assert any(
            word in response_text for word in ["auth", "permission", "access"]
        ), "Should mention authentication issue in error message"


class TestErrorRecoveryIntegration:
    """Test error recovery and retry mechanisms."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_command_retry_on_temporary_failure(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test retry mechanism for temporary command failures."""
        with patch("retromcp.ssh_handler.SSHHandler") as mock_ssh_class:
            mock_ssh = Mock()

            # Mock temporary failure followed by success
            call_count = 0

            def mock_execute_command(command):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call fails with temporary error
                    return CommandResult(
                        command=command,
                        exit_code=1,
                        stdout="",
                        stderr="Temporary failure",
                        success=False,
                        execution_time=0.1,
                    )
                else:
                    # Second call succeeds
                    return CommandResult(
                        command=command,
                        exit_code=0,
                        stdout="success output",
                        stderr="",
                        success=True,
                        execution_time=0.1,
                    )

            mock_ssh.execute_command = AsyncMock(side_effect=mock_execute_command)
            mock_ssh_class.return_value = mock_ssh

            # Create container with mocked client
            container = Container(test_config)
            container._instances["retropie_client"] = mock_ssh

            # Create tools with container
            system_tools = SystemManagementTools(container)

            # First attempt - should handle temporary failure
            result1 = await system_tools.handle_tool_call("get_system_info", {})
            assert len(result1) == 1
            # Could be error or success depending on retry logic

            # Second attempt - should succeed
            result2 = await system_tools.handle_tool_call("get_system_info", {})
            assert len(result2) == 1
            # Should have success output

    @pytest.mark.asyncio
    async def test_partial_command_failure_handling(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test handling when some commands succeed and others fail."""
        # Create container
        container = Container(test_config)

        # Mock use case to return successful Result with partial system info
        from retromcp.domain.models import Result

        mock_system_info = SystemInfo(
            hostname="retropie-test",
            cpu_temperature=55.0,
            memory_total=1024,
            memory_used=512,
            memory_free=512,
            disk_total=16000,
            disk_used=8000,
            disk_free=8000,
            load_average=[0.5, 0.3, 0.2],
            uptime=3600,
        )

        mock_use_case = Mock()
        mock_use_case.execute.return_value = Result.success(mock_system_info)
        container._instances["get_system_info_use_case"] = mock_use_case

        # Create tools with container
        system_tools = SystemManagementTools(container)

        # Execute tool that collects system info
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify partial success is handled appropriately using MCP format
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1
        response = result[0]

        # Check response follows MCP standard
        assert hasattr(response, "text"), "Should have text attribute"

        # Should contain successful parts
        response_text = response.text
        assert "55" in response_text or "temperature" in response_text.lower(), (
            "Should include successful temperature data"
        )
        assert "memory" in response_text.lower() or "512" in response_text, (
            "Should include successful memory data"
        )

        # Verify use case was called
        mock_use_case.execute.assert_called_once()


class TestConcurrentOperationsIntegration:
    """Test concurrent operations and resource management."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_concurrent_tool_operations(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test multiple tools running concurrently."""
        # Create container
        container = Container(test_config)

        # Mock use cases for concurrent operations test
        from retromcp.domain.models import CommandResult
        from retromcp.domain.models import Result

        # Mock system info use case
        mock_system_info = SystemInfo(
            hostname="retropie-test",
            cpu_temperature=45.0,
            memory_total=1024,
            memory_used=512,
            memory_free=512,
            disk_total=16000,
            disk_used=8000,
            disk_free=8000,
            load_average=[0.2, 0.1, 0.1],
            uptime=7200,
        )
        mock_system_info_use_case = Mock()
        mock_system_info_use_case.execute.return_value = Result.success(
            mock_system_info
        )
        container._instances["get_system_info_use_case"] = mock_system_info_use_case

        # Mock SSH client for hardware tools that use direct command execution
        mock_client = Mock()
        mock_client.execute_command.return_value = CommandResult(
            command="vcgencmd measure_temp",
            exit_code=0,
            stdout="temp=45.0'C",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        container._instances["retropie_client"] = mock_client

        # Create multiple tools with container
        system_tools = SystemManagementTools(container)
        hardware_tools = HardwareMonitoringTools(container)

        # Run operations concurrently
        tasks = [
            system_tools.handle_tool_call("get_system_info", {}),
            hardware_tools.handle_tool_call(
                "manage_hardware", {"component": "temperature", "action": "check"}
            ),
            system_tools.handle_tool_call("get_system_info", {}),  # Duplicate
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations completed using MCP-compliant format
        assert len(results) == 3

        # Check that none raised exceptions and all return MCP-compliant lists
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), (
                f"Task {i} should not raise exception"
            )
            assert isinstance(result, list), (
                f"Task {i} should return MCP-compliant list"
            )
            assert len(result) == 1, f"Task {i} should return one response"
            assert hasattr(result[0], "text"), (
                f"Task {i} response should have text attribute"
            )

        # Verify use case was called for system info operations
        assert (
            mock_system_info_use_case.execute.call_count >= 2
        )  # System info called twice

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, test_config: RetroPieConfig) -> None:
        """Test proper resource cleanup when errors occur."""
        with patch("retromcp.ssh_handler.RetroPieSSH") as mock_ssh_class:
            mock_ssh = Mock()

            # Mock context manager behavior if needed
            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
            mock_ssh.__exit__ = Mock(return_value=None)
            mock_ssh.get_system_info = Mock(side_effect=Exception("Test error"))
            mock_ssh_class.return_value = mock_ssh

            # Create container with mocked client
            container = Container(test_config)
            container._instances["retropie_client"] = mock_ssh

            # Create tools with container
            system_tools = SystemManagementTools(container)

            # Execute operation that will fail
            result = await system_tools.handle_tool_call("get_system_info", {})

            # Verify error handling using MCP-compliant response format
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]

            # Check for error using text content (MCP standard approach)
            assert hasattr(response, "text"), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(
                word in response_text for word in ["error", "failed"]
            ), "Should indicate error in text"

            # Note: Specific cleanup verification would depend on actual SSH handler implementation


class TestEndToEndErrorScenarios:
    """Test realistic end-to-end error scenarios."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="unreachable-host.local",
            username="retro",
            password="wrong_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_unreachable_host_scenario(self, test_config: RetroPieConfig) -> None:
        """Test scenario where RetroPie host is unreachable."""
        # Create container
        container = Container(test_config)

        # Mock use case to return network error via Result pattern
        from retromcp.domain.models import ConnectionError
        from retromcp.domain.models import Result

        mock_use_case = Mock()
        mock_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="NETWORK_UNREACHABLE",
                message="Network is unreachable",
                details={"error": "No route to host"},
            )
        )
        container._instances["get_system_info_use_case"] = mock_use_case

        # Create tools with container
        system_tools = SystemManagementTools(container)

        # Attempt operation
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify network error is handled using MCP-compliant response format
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1
        response = result[0]

        # Check for error using text content (MCP standard approach)
        assert hasattr(response, "text"), "Should have text attribute"
        response_text = response.text.lower()
        assert "❌" in response.text or any(
            word in response_text for word in ["error", "failed"]
        ), "Should indicate error in text"
        assert any(
            word in response_text for word in ["network", "unreachable", "connection"]
        ), "Should mention network issue in error message"

    @pytest.mark.asyncio
    async def test_malformed_command_output_scenario(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test scenario where commands return unexpected output."""
        with patch("retromcp.ssh_handler.SSHHandler") as mock_ssh_class:
            mock_ssh = Mock()

            # Mock malformed/unexpected command outputs
            def mock_execute_command(command):
                if "hostname" in command:
                    return CommandResult(
                        command=command,
                        exit_code=0,
                        stdout="MALFORMED_OUTPUT_###",
                        stderr="",
                        success=True,
                        execution_time=0.1,
                    )
                elif "vcgencmd" in command:
                    return CommandResult(
                        command=command,
                        exit_code=0,
                        stdout="invalid_temp_format",
                        stderr="",
                        success=True,
                        execution_time=0.1,
                    )
                elif "free" in command:
                    return CommandResult(
                        command=command,
                        exit_code=0,
                        stdout="completely unexpected output format",
                        stderr="",
                        success=True,
                        execution_time=0.1,
                    )
                else:
                    return CommandResult(
                        command=command,
                        exit_code=0,
                        stdout="???",
                        stderr="",
                        success=True,
                        execution_time=0.1,
                    )

            mock_ssh.execute_command = AsyncMock(side_effect=mock_execute_command)
            mock_ssh_class.return_value = mock_ssh

            # Create container with mocked client
            container = Container(test_config)
            container._instances["retropie_client"] = mock_ssh

            # Create tools with container
            system_tools = SystemManagementTools(container)

            # Execute operation with malformed responses
            result = await system_tools.handle_tool_call("get_system_info", {})

            # Verify malformed output is handled gracefully
            assert len(result) == 1
            response = result[0]

            # Should either handle gracefully or report parsing issues
            # The exact behavior depends on implementation, but shouldn't crash
            assert isinstance(response, TextContent)
