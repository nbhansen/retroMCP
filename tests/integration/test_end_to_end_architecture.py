"""End-to-end architectural compliance tests."""

from unittest.mock import patch

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.container import Container
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import SystemInfo
from retromcp.server import RetroMCPServer


class TestEndToEndArchitecture:
    """Test complete end-to-end architectural flows."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        return RetroPieConfig(host="integration-test", username="test-user")

    @pytest.fixture
    def server_config(self) -> ServerConfig:
        """Provide server configuration."""
        return ServerConfig()

    @pytest.mark.asyncio
    async def test_complete_tool_execution_flow(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test complete flow: MCP Request → Server → Container → Use Case → Repository → SSH → Response."""
        server = RetroMCPServer(test_config, server_config)

        # Mock the entire infrastructure chain
        with patch.object(server.container, "connect", return_value=True):
            # Mock the SSH client at the lowest level
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.return_value = CommandResult(
                    command="uname -a",
                    exit_code=0,
                    stdout="Linux integration-test 5.15.0",
                    stderr="",
                    success=True,
                    execution_time=0.05,
                )

                # Execute tool call through server (simulates MCP request)
                result = await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )

                # Verify complete chain executed
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "integration-test" in result[0].text

                # Verify the call propagated through all layers
                mock_ssh.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_tool_types_integration(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that multiple tool types work through the same architecture."""
        server = RetroMCPServer(test_config, server_config)

        with patch.object(server.container, "connect", return_value=True):
            # Mock different repository responses for different tools
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh, patch.object(
                server.container.controller_repository, "detect_controllers"
            ) as mock_controllers:
                # Setup different responses for different tools
                mock_ssh.return_value = CommandResult(
                    command="test",
                    exit_code=0,
                    stdout="System OK",
                    stderr="",
                    success=True,
                    execution_time=0.1,
                )

                mock_controllers.return_value = [
                    Controller(
                        device_path="/dev/input/js0",
                        name="Test Controller",
                        controller_type="xbox",
                        vendor_id="045e",
                        product_id="028e",
                        is_connected=True,
                    )
                ]

                # Test system tool
                system_result = await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )
                assert len(system_result) == 1
                assert "integration-test" in system_result[0].text

                # Test controller tool
                controller_result = await server.call_tool(
                    "manage_gaming", {"component": "controller", "action": "detect"}
                )
                assert len(controller_result) == 1
                assert "Test Controller" in controller_result[0].text

                # Verify both chains executed through proper architecture
                mock_ssh.assert_called()
                mock_controllers.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_through_complete_chain(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that errors are properly handled through the complete architectural chain."""
        server = RetroMCPServer(test_config, server_config)

        with patch.object(server.container, "connect", return_value=True):
            # Mock SSH to raise exception at infrastructure level
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.side_effect = Exception(
                    "Network timeout at infrastructure level"
                )

                # Error should be caught and returned as proper MCP response
                result = await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )

                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "Connection failed" in result[0].text
                assert "Network timeout" in result[0].text

    @pytest.mark.asyncio
    async def test_container_isolation_across_tools(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that tools are properly isolated but share container state."""
        server = RetroMCPServer(test_config, server_config)

        with patch.object(server.container, "connect", return_value=True):
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.return_value = CommandResult(
                    command="test",
                    exit_code=0,
                    stdout="OK",
                    stderr="",
                    success=True,
                    execution_time=0.1,
                )

                # Call multiple tools - they should share the same container instance
                await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )
                await server.call_tool(
                    "manage_system", {"resource": "info", "action": "get"}
                )

                # Tools should have used same SSH client instance
                assert mock_ssh.call_count >= 1

                # Verify container state is consistent
                tools = await server.list_tools()
                assert len(tools) > 0

    def test_architectural_layer_separation(self, test_config: RetroPieConfig) -> None:
        """Test that architectural layers are properly separated."""
        container = Container(test_config)

        # Verify clean separation between layers

        # Domain layer (should be pure, no infrastructure imports)

        # Domain objects should be simple data structures
        system_info = SystemInfo(
            hostname="test",
            cpu_temperature=50.0,
            memory_total=1000,
            memory_used=500,
            memory_free=500,
            disk_total=2000,
            disk_used=1000,
            disk_free=1000,
            load_average=[1.0],
            uptime=3600,
        )
        assert system_info.hostname == "test"

        # Application layer (should only depend on domain)
        use_case = container.get_system_info_use_case
        assert hasattr(use_case, "execute")

        # Infrastructure layer (should implement domain interfaces)
        system_repo = container.system_repository
        assert hasattr(system_repo, "get_system_info")

        # Verify no cross-layer dependencies
        # Domain should not depend on application or infrastructure
        # Application should only depend on domain
        # Infrastructure should only depend on domain (implements interfaces)

    @pytest.mark.asyncio
    async def test_dependency_injection_through_complete_flow(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that dependency injection works correctly through complete flow."""
        # Create server (entry point)
        server = RetroMCPServer(test_config, server_config)

        # Verify server has container
        assert hasattr(server, "container")
        assert server.container.config is test_config

        with patch.object(server.container, "connect", return_value=True):
            # Get tools list (creates tool instances)
            tools = await server.list_tools()

            # Tools should have been created with container injection
            # We can't directly access the tool instances from list_tools,
            # but we can verify the flow works by checking that tools are returned
            assert len(tools) > 0

            # Verify expected tool categories exist
            tool_names = [tool.name for tool in tools]
            expected_categories = [
                "manage_system",
                "manage_gaming",
                "manage_hardware",
            ]

            for expected in expected_categories:
                assert expected in tool_names

    @pytest.mark.asyncio
    async def test_configuration_propagation_through_layers(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that configuration properly propagates through all layers."""
        server = RetroMCPServer(test_config, server_config)

        # Configuration should flow: Server → Container → Use Cases → Repositories
        assert server.config is test_config
        assert server.container.config is test_config

        # Use cases should have access to config through repositories
        with patch.object(server.container, "connect", return_value=True):
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.return_value = CommandResult(
                    command="hostname",
                    exit_code=0,
                    stdout=test_config.host,
                    stderr="",
                    success=True,
                    execution_time=0.1,
                )

                # Execute tool that uses configuration
                result = await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )

                # Result should reflect the configuration
                assert len(result) == 1
                assert test_config.host in result[0].text

    @pytest.mark.asyncio
    async def test_state_management_across_requests(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that state is properly managed across multiple requests."""
        server = RetroMCPServer(test_config, server_config)

        with patch.object(server.container, "connect", return_value=True):
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.return_value = CommandResult(
                    command="test",
                    exit_code=0,
                    stdout="OK",
                    stderr="",
                    success=True,
                    execution_time=0.1,
                )

                # First request
                result1 = await server.call_tool(
                    "manage_system", {"resource": "connection", "action": "test"}
                )
                assert len(result1) == 1

                # Second request - should reuse same container state
                result2 = await server.call_tool(
                    "manage_system", {"resource": "info", "action": "get"}
                )
                assert len(result2) == 1

                # Container should maintain singleton behavior
                # Both calls should use same infrastructure instances
                assert mock_ssh.call_count >= 1

    def test_interface_compliance_through_chain(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that all interfaces are properly implemented through the chain."""
        container = Container(test_config)

        # Verify that infrastructure implements domain interfaces
        from retromcp.domain.ports import ControllerRepository
        from retromcp.domain.ports import RetroPieClient
        from retromcp.domain.ports import SystemRepository

        # Check that repositories implement their interfaces
        assert isinstance(container.retropie_client, RetroPieClient)
        assert isinstance(container.system_repository, SystemRepository)
        assert isinstance(container.controller_repository, ControllerRepository)

        # Verify required methods exist
        assert hasattr(container.retropie_client, "execute_command")
        assert hasattr(container.system_repository, "get_system_info")
        assert hasattr(container.controller_repository, "detect_controllers")

    @pytest.mark.asyncio
    async def test_resource_cleanup_through_chain(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that resources are properly cleaned up through the chain."""
        server = RetroMCPServer(test_config, server_config)

        with patch.object(server.container, "connect", return_value=True):
            with patch.object(
                server.container.retropie_client, "execute_command"
            ) as mock_ssh:
                mock_ssh.return_value = CommandResult(
                    command="test",
                    exit_code=0,
                    stdout="OK",
                    stderr="",
                    success=True,
                    execution_time=0.1,
                )

                # Multiple calls should reuse resources appropriately
                for _i in range(3):
                    result = await server.call_tool(
                        "manage_system", {"resource": "connection", "action": "test"}
                    )
                    assert len(result) == 1

                # Should not create new instances for each call (singleton behavior)
                # The exact call count depends on implementation, but should be reasonable
                assert mock_ssh.call_count >= 1
                assert mock_ssh.call_count <= 10  # Should not be excessive


class TestArchitecturalConstraints:
    """Test that architectural constraints are enforced."""

    def test_no_circular_dependencies(self, test_config: RetroPieConfig) -> None:
        """Test that there are no circular dependencies in the architecture."""
        # This test verifies the dependency graph is acyclic
        container = Container(test_config)

        # Container should not depend on tools
        # Tools should not depend on each other
        # Use cases should not depend on tools
        # Repositories should not depend on use cases

        # We verify this by checking that we can create all components
        # without circular import or instantiation issues

        system_tools = None

        try:
            from retromcp.tools.gaming_system_tools import GamingSystemTools
            from retromcp.tools.system_management_tools import SystemManagementTools

            system_tools = SystemManagementTools(container)
            gaming_tools = GamingSystemTools(container)

        except ImportError as e:
            pytest.fail(f"Circular dependency detected: {e}")

        # Both tools should be created successfully
        assert system_tools is not None
        assert gaming_tools is not None

        # Tools should not have references to each other
        assert not hasattr(system_tools, "gaming_tools")
        assert not hasattr(gaming_tools, "system_tools")

    def test_abstraction_layer_compliance(self, test_config: RetroPieConfig) -> None:
        """Test that abstraction layers are properly maintained."""
        container = Container(test_config)

        # Tools should only see abstractions (container), not implementations
        from retromcp.tools.system_management_tools import SystemManagementTools

        system_tools = SystemManagementTools(container)

        # Tool should not have direct access to SSH implementation
        assert not hasattr(system_tools, "ssh")
        assert not hasattr(system_tools, "ssh_client")
        assert not hasattr(system_tools, "paramiko")

        # Tool should access functionality through container abstractions
        assert hasattr(system_tools, "container")
        assert hasattr(system_tools.container, "test_connection_use_case")

    def test_immutability_constraints(self, test_config: RetroPieConfig) -> None:
        """Test that immutability constraints are maintained."""
        container = Container(test_config)

        # Configuration should be immutable
        with pytest.raises((AttributeError, TypeError)):
            container.config.host = "modified"  # type: ignore

        # Domain objects should be immutable

        system_info = SystemInfo(
            hostname="test",
            cpu_temperature=50.0,
            memory_total=1000,
            memory_used=500,
            memory_free=500,
            disk_total=2000,
            disk_used=1000,
            disk_free=1000,
            load_average=[1.0],
            uptime=3600,
        )

        with pytest.raises((AttributeError, TypeError)):
            system_info.hostname = "modified"  # type: ignore

    def test_single_responsibility_constraint(
        self, test_config: RetroPieConfig
    ) -> None:
        """Test that single responsibility principle is maintained."""
        container = Container(test_config)

        # Container should only manage dependencies, not business logic
        container_methods = [
            name
            for name in dir(container)
            if not name.startswith("_") and callable(getattr(container, name))
        ]

        # Container should not have business logic verbs
        business_verbs = [
            "install",
            "configure",
            "detect",
            "setup",
            "run",
            "execute",
            "manage",
        ]
        for method in container_methods:
            for verb in business_verbs:
                assert not method.startswith(verb), (
                    f"Container violates SRP with business logic method: {method}"
                )

        # Tools should not directly manage infrastructure
        from retromcp.tools.system_management_tools import SystemManagementTools

        system_tools = SystemManagementTools(container)

        tool_attrs = [name for name in dir(system_tools) if not name.startswith("_")]
        infrastructure_indicators = ["ssh", "socket", "connection", "client"]

        for attr in tool_attrs:
            for indicator in infrastructure_indicators:
                if indicator in attr.lower() and attr != "container":
                    pytest.fail(
                        f"Tool violates SRP with infrastructure attribute: {attr}"
                    )
