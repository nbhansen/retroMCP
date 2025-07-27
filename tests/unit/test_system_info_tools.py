"""Unit tests for SystemInfoTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent
from mcp.types import Tool

from retromcp.domain.models import Result
from retromcp.domain.models import SystemInfo
from retromcp.tools.system_info_tools import SystemInfoTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.system_info_tools
class TestSystemInfoTools:
    """Test cases for SystemInfoTools class."""

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Provide mocked container with system info use case."""
        mock = Mock()
        mock.get_system_info_use_case = Mock()
        return mock

    @pytest.fixture
    def system_info_tools(self, mock_container: Mock) -> SystemInfoTools:
        """Provide SystemInfoTools instance with mocked dependencies."""
        return SystemInfoTools(mock_container)

    @pytest.fixture
    def sample_system_info(self) -> SystemInfo:
        """Provide sample system information for testing."""
        return SystemInfo(
            hostname="test-retropie",
            cpu_temperature=65.2,
            memory_total=1073741824,  # 1GB
            memory_used=536870912,  # 512MB
            memory_free=536870912,  # 512MB
            disk_total=32212254720,  # ~30GB
            disk_used=16106127360,  # ~15GB
            disk_free=16106127360,  # ~15GB
            load_average="0.5, 0.3, 0.1",
            uptime=86400,  # 1 day
        )

    def test_get_tools_returns_system_info_tool(
        self, system_info_tools: SystemInfoTools
    ) -> None:
        """Test that get_tools returns the get_system_info tool with correct schema."""
        # Act
        tools = system_info_tools.get_tools()

        # Assert
        assert len(tools) == 1
        tool = tools[0]
        assert isinstance(tool, Tool)
        assert tool.name == "get_system_info"
        assert "comprehensive system information" in tool.description

        # Verify schema structure
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "category" in schema["properties"]

        # Verify category enum contains all expected values
        category_enum = schema["properties"]["category"]["enum"]
        expected_categories = [
            "all",
            "hardware",
            "network",
            "storage",
            "processes",
            "services",
        ]
        assert all(cat in category_enum for cat in expected_categories)

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool_returns_error(
        self, system_info_tools: SystemInfoTools
    ) -> None:
        """Test that unknown tool names return error response."""
        # Act
        result = await system_info_tools.handle_tool_call("unknown_tool", {})

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_info_success_all_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'all' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "all"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains all sections for 'all' category
        assert "System Information:" in response_text
        assert "🖥️ Hardware:" in response_text
        assert "💾 Memory:" in response_text
        assert "💽 Storage:" in response_text
        assert "test-retropie" in response_text
        assert "65.2°C" in response_text
        assert "1024.0 MB" in response_text  # Total memory
        assert "512.0 MB" in response_text  # Used/Free memory
        assert "30.0 GB" in response_text  # Total disk

    @pytest.mark.asyncio
    async def test_handle_system_info_success_hardware_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'hardware' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "hardware"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains only hardware information
        assert "🖥️ Hardware Information:" in response_text
        assert "test-retropie" in response_text
        assert "65.2°C" in response_text
        assert "0.5, 0.3, 0.1" in response_text
        assert "86400" in response_text

        # Should NOT contain memory/storage sections
        assert "💾 Memory:" not in response_text
        assert "💽 Storage:" not in response_text

    @pytest.mark.asyncio
    async def test_handle_system_info_success_network_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'network' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "network"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains network information
        assert "🌐 Network Information:" in response_text
        assert "test-retropie" in response_text
        assert "Network interfaces and details would be shown here" in response_text

    @pytest.mark.asyncio
    async def test_handle_system_info_success_storage_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'storage' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "storage"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains storage information
        assert "💽 Storage Information:" in response_text
        assert "30.0 GB" in response_text  # Total
        assert "15.0 GB" in response_text  # Used/Free
        assert "50.0%" in response_text  # Usage percentage

    @pytest.mark.asyncio
    async def test_handle_system_info_success_processes_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'processes' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "processes"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains process information
        assert "⚙️ Process Information:" in response_text
        assert "0.5, 0.3, 0.1" in response_text  # Load average
        assert "50.0%" in response_text  # Memory usage percentage
        assert "Process details would be shown here" in response_text

    @pytest.mark.asyncio
    async def test_handle_system_info_success_services_category(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test successful system info retrieval with 'services' category."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "services"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Verify it contains service information
        assert "🔧 Service Information:" in response_text
        assert "86400" in response_text  # Uptime
        assert "Service status details would be shown here" in response_text

    @pytest.mark.asyncio
    async def test_handle_system_info_unknown_category_returns_error(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test that unknown category returns error response."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "invalid_category"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown category: invalid_category" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_info_use_case_error_returns_error(
        self, system_info_tools: SystemInfoTools, mock_container: Mock
    ) -> None:
        """Test that use case error returns error response."""
        from retromcp.domain.models import ExecutionError

        # Arrange
        error = ExecutionError(
            code="SYSTEM_INFO_FAILED",
            message="Failed to retrieve system information",
            command="system info",
            exit_code=1,
            stderr="SSH connection failed",
        )
        mock_container.get_system_info_use_case.execute.return_value = Result.error(
            error
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "all"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "Failed to get system info: Failed to retrieve system information"
            in result[0].text
        )

    @pytest.mark.asyncio
    async def test_handle_system_info_exception_returns_error(
        self, system_info_tools: SystemInfoTools, mock_container: Mock
    ) -> None:
        """Test that exceptions in system info retrieval return error response."""
        # Arrange
        mock_container.get_system_info_use_case.execute.side_effect = Exception(
            "Unexpected error"
        )

        # Act
        result = await system_info_tools.handle_tool_call(
            "get_system_info", {"category": "all"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "System info error: Unexpected error" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_info_default_category_is_all(
        self,
        system_info_tools: SystemInfoTools,
        mock_container: Mock,
        sample_system_info: SystemInfo,
    ) -> None:
        """Test that default category is 'all' when not specified."""
        # Arrange
        mock_container.get_system_info_use_case.execute.return_value = Result.success(
            sample_system_info
        )

        # Act - no category specified
        result = await system_info_tools.handle_tool_call("get_system_info", {})

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        response_text = result[0].text

        # Should contain all sections like 'all' category
        assert "System Information:" in response_text
        assert "🖥️ Hardware:" in response_text
        assert "💾 Memory:" in response_text
        assert "💽 Storage:" in response_text

    def test_format_methods_handle_edge_cases(
        self, system_info_tools: SystemInfoTools
    ) -> None:
        """Test that formatting methods handle edge cases properly."""
        # Create system info with edge case values
        edge_case_info = SystemInfo(
            hostname="",
            cpu_temperature=0.0,
            memory_total=0,
            memory_used=0,
            memory_free=0,
            disk_total=1,  # Avoid division by zero
            disk_used=0,
            disk_free=1,
            load_average="",
            uptime=0,
        )

        # Test each formatter method
        complete_info = system_info_tools._format_complete_system_info(edge_case_info)
        assert "0.0°C" in complete_info
        assert "0.0 MB" in complete_info
        assert "0.0 GB" in complete_info

        hardware_info = system_info_tools._format_hardware_info(edge_case_info)
        assert "0.0°C" in hardware_info

        network_info = system_info_tools._format_network_info(edge_case_info)
        assert "Network Information:" in network_info

        storage_info = system_info_tools._format_storage_info(edge_case_info)
        assert "0.0 GB" in storage_info
        assert "0.0%" in storage_info

        # Create new SystemInfo with memory_total=1 to avoid division by zero
        memory_test_info = SystemInfo(
            hostname="",
            cpu_temperature=0.0,
            memory_total=1,  # Non-zero to avoid division by zero
            memory_used=0,
            memory_free=1,
            disk_total=1,
            disk_used=0,
            disk_free=1,
            load_average="",
            uptime=0,
        )
        process_info = system_info_tools._format_process_info(memory_test_info)
        assert "0.0%" in process_info

        service_info = system_info_tools._format_service_info(edge_case_info)
        assert "Service Information:" in service_info
