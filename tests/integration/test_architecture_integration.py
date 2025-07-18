"""Integration tests for architectural compliance and dependency chains."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.container import Container
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.server import RetroMCPServer
from retromcp.tools.gaming_system_tools import GamingSystemTools
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools
from retromcp.tools.system_management_tools import SystemManagementTools


class TestArchitecturalIntegration:
    """Test that architectural patterns work correctly in integration."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        return RetroPieConfig(host="test-host", username="test-user")

    @pytest.fixture
    def server_config(self) -> ServerConfig:
        """Provide server configuration."""
        return ServerConfig()

    @pytest.fixture
    def mock_ssh_client(self) -> Mock:
        """Provide mocked SSH client."""
        mock = Mock()
        mock.connect.return_value = True
        mock.execute_command.return_value = CommandResult(
            command="test",
            exit_code=0,
            stdout="success",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        return mock

    def test_complete_dependency_chain_system_tools(
        self, test_config: RetroPieConfig, mock_ssh_client: Mock
    ) -> None:
        """Test complete dependency chain from Container → Use Cases → Repositories → SSH."""
        # Create container with mocked SSH client
        container = Container(test_config)

        # Mock the SSH client at the infrastructure level
        with patch.object(
            container, "_instances", {"retropie_client": Mock()}
        ) as mock_instances:
            mock_client = mock_instances["retropie_client"]
            mock_client.execute_command.return_value = CommandResult(
                command="test",
                exit_code=0,
                stdout="System OK",
                stderr="",
                success=True,
                execution_time=0.1,
            )

            # Create SystemManagementTools with container
            system_tools = SystemManagementTools(container)

            # Test that tools can access use cases through container
            assert hasattr(system_tools.container, "test_connection_use_case")
            assert hasattr(system_tools.container, "get_system_info_use_case")
            assert hasattr(system_tools.container, "install_packages_use_case")

            # Verify container provides access to repositories
            assert hasattr(system_tools.container, "system_repository")
            assert hasattr(system_tools.container, "controller_repository")
            assert hasattr(system_tools.container, "retropie_client")

    def test_complete_dependency_chain_controller_tools(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test complete dependency chain for controller tools."""
        container = Container(test_config)

        # Mock the controller repository with the actual repository instance
        from unittest.mock import Mock
        mock_repo = Mock()
        mock_repo.detect_controllers.return_value = [
            Controller(
                device_path="/dev/input/js0",
                name="Xbox Controller",
                controller_type="xbox",
                vendor_id="045e",
                product_id="028e",
                connected=True,
            )
        ]

        # Replace the repository instance in container's instances
        container._instances["controller_repository"] = mock_repo

        controller_tools = GamingSystemTools(container)

        # Verify access to use cases
        assert hasattr(controller_tools.container, "detect_controllers_use_case")
        assert hasattr(controller_tools.container, "setup_controller_use_case")

    def test_server_container_integration(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that server properly integrates with container and tools."""
        server = RetroMCPServer(test_config, server_config)

        # Verify server has container
        assert hasattr(server, "container")
        assert isinstance(server.container, Container)

        # Verify container has proper configuration
        assert server.container.config == test_config

    @pytest.mark.asyncio
    async def test_tool_instantiation_through_server(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that server can properly instantiate all tools with container."""
        server = RetroMCPServer(test_config, server_config)

        # Mock the container's connect method to avoid actual SSH
        with patch.object(server.container, "connect", return_value=True):
            # Get tools list - this creates tool instances internally
            tools = await server.list_tools()

            # Verify tools were created (should not be empty or error tools)
            assert len(tools) > 0
            tool_names = [tool.name for tool in tools]

            # Verify expected tools exist
            expected_tools = [
                "manage_service",
                "manage_gaming",
                "manage_hardware",
            ]

            for expected_tool in expected_tools:
                assert expected_tool in tool_names, (
                    f"Tool {expected_tool} not found in {tool_names}"
                )

    def test_dependency_injection_consistency(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that all tools follow consistent dependency injection patterns."""
        container = Container(test_config)

        # Create all tool types
        tools = [
            SystemManagementTools(container),
            GamingSystemTools(container),
            HardwareMonitoringTools(container),
        ]

        for tool in tools:
            # Verify all tools have container
            assert hasattr(tool, "container")
            assert tool.container is container

            # Verify all tools have config through container
            assert hasattr(tool, "config")
            assert tool.config is container.config

            # Verify all tools can get their MCP tools list
            tool_list = tool.get_tools()
            assert isinstance(tool_list, list)
            assert len(tool_list) > 0

    def test_use_case_accessibility_through_container(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that use cases are accessible through container."""
        container = Container(test_config)

        # Test that use cases are accessible
        use_cases = [
            "test_connection_use_case",
            "get_system_info_use_case",
            "install_packages_use_case",
            "update_system_use_case",
            "detect_controllers_use_case",
            "setup_controller_use_case",
            "install_emulator_use_case",
        ]

        for use_case_name in use_cases:
            assert hasattr(container, use_case_name), (
                f"Use case {use_case_name} not found"
            )

            # Get the use case - should not raise exception
            use_case = getattr(container, use_case_name)
            assert use_case is not None

            # Use cases should have execute method
            assert hasattr(use_case, "execute")

    def test_repository_accessibility_through_container(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that repositories are accessible through container."""
        container = Container(test_config)

        # Test that repositories are accessible
        repositories = [
            "system_repository",
            "controller_repository",
            "emulator_repository",
            "retropie_client",
        ]

        for repo_name in repositories:
            assert hasattr(container, repo_name), f"Repository {repo_name} not found"

            # Get the repository - should not raise exception
            repository = getattr(container, repo_name)
            assert repository is not None

    @pytest.mark.asyncio
    async def test_end_to_end_tool_execution_flow(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test complete end-to-end flow from server to repository layer."""
        server = RetroMCPServer(test_config, server_config)

        # Mock the infrastructure layer
        with patch.object(server.container, "connect", return_value=True):
            # Replace the retropie_client with a mock
            from unittest.mock import Mock
            mock_client = Mock()
            mock_execute = mock_client.execute_command
            server.container._instances["retropie_client"] = mock_client
            mock_execute.return_value = CommandResult(
                command="uname -a",
                exit_code=0,
                stdout="Linux test-host",
                stderr="",
                success=True,
                execution_time=0.1,
            )

            # Execute a tool call through the server
            result = await server.call_tool(
                "manage_connection", {"action": "test"}
            )

            # Verify result structure
            assert len(result) == 1
            assert hasattr(result[0], "text")

            # Verify the call went through the proper chain:
            # Server → Container → Use Case → Repository → SSH Client
            mock_execute.assert_called()

    def test_container_singleton_behavior(self, test_config: RetroPieConfig) -> None:
        """Test that container properly manages singleton instances."""
        container = Container(test_config)

        # Get same use case multiple times
        use_case1 = container.test_connection_use_case
        use_case2 = container.test_connection_use_case

        # Should be same instance (singleton)
        assert use_case1 is use_case2

        # Same for repositories
        repo1 = container.system_repository
        repo2 = container.system_repository

        assert repo1 is repo2

    def test_configuration_immutability_through_chain(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that configuration remains immutable through the dependency chain."""
        container = Container(test_config)
        system_tools = SystemManagementTools(container)

        # Config should be same reference through the chain
        assert system_tools.config is container.config
        assert system_tools.config is test_config

        # Should be frozen (immutable)
        with pytest.raises((AttributeError, TypeError)):
            system_tools.config.host = "modified"  # type: ignore

    def test_error_propagation_through_dependency_chain(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that errors properly propagate through the dependency chain."""
        container = Container(test_config)

        # Mock repository to raise exception by replacing the instance
        from unittest.mock import Mock
        mock_client = Mock()
        mock_client.execute_command.side_effect = Exception("SSH connection failed")
        container._instances["retropie_client"] = mock_client

        SystemManagementTools(container)

        # Create system tools and test exception propagation
        system_tools = SystemManagementTools(container)

        # Exception should propagate through the tool chain when calling manage_connection
        # This goes: Tool → Container → Use Case → Repository → SSH (exception)
        import asyncio

        async def test_exception_propagation():
            result = await system_tools.handle_tool_call("manage_connection", {"action": "test"})
            # Should return error response, not raise exception
            assert len(result) == 1
            assert "❌" in result[0].text or "error" in result[0].text.lower()

        # Run the async test
        asyncio.run(test_exception_propagation())


class TestArchitecturalCompliance:
    """Test that the architecture follows clean architecture principles."""

    def test_dependency_direction_compliance(self, test_config: RetroPieConfig) -> None:
        """Test that dependencies flow in the correct direction."""
        container = Container(test_config)
        system_tools = SystemManagementTools(container)

        # Tools should depend on container (abstraction)
        assert hasattr(system_tools, "container")

        # Tools should not have direct access to SSH or infrastructure
        assert not hasattr(system_tools, "ssh")
        assert not hasattr(system_tools, "ssh_client")
        assert not hasattr(system_tools, "ssh_handler")

        # Container should provide access to use cases (domain layer)
        assert hasattr(container, "test_connection_use_case")

        # Use cases should not be directly accessible from tools (must go through container)
        assert not hasattr(system_tools, "test_connection_use_case")

    def test_interface_segregation_compliance(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that interfaces are properly segregated."""
        container = Container(test_config)

        # Different repositories should have different interfaces
        system_repo = container.system_repository
        controller_repo = container.controller_repository

        # System repository should have system-specific methods
        assert hasattr(system_repo, "get_system_info")
        assert hasattr(system_repo, "install_packages")

        # Controller repository should have controller-specific methods
        assert hasattr(controller_repo, "detect_controllers")
        assert hasattr(controller_repo, "setup_controller")  # Updated method name

        # System repo should not have controller methods
        assert not hasattr(system_repo, "detect_controllers")
        # Controller repo should not have system methods
        assert not hasattr(controller_repo, "get_system_info")

    def test_single_responsibility_compliance(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that components have single responsibilities."""
        container = Container(test_config)

        # Container should only manage dependencies
        container_methods = [
            name
            for name in dir(container)
            if not name.startswith("_") and callable(getattr(container, name))
        ]

        # Container should not have business logic methods
        business_logic_indicators = ["install", "configure", "detect", "run", "execute"]
        for method in container_methods:
            for indicator in business_logic_indicators:
                assert not method.startswith(indicator), (
                    f"Container has business logic method: {method}"
                )

        # Use cases should have single execute method
        use_case = container.test_connection_use_case
        use_case_methods = [
            name
            for name in dir(use_case)
            if not name.startswith("_") and callable(getattr(use_case, name))
        ]

        # Use case should primarily have execute method
        assert "execute" in use_case_methods
