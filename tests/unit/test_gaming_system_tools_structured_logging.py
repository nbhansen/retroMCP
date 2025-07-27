"""Unit tests for GamingSystemTools structured logging integration."""

from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.infrastructure.structured_logger import ErrorCategory
from retromcp.tools.gaming_system_tools import GamingSystemTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.gaming_tools
class TestGamingSystemToolsStructuredLogging:
    """Test cases for GamingSystemTools structured logging integration."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with structured logger."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config

        # Mock structured logger
        mock.structured_logger = Mock()
        mock.structured_logger.generate_correlation_id = Mock(
            return_value="test-correlation-123"
        )
        mock.structured_logger.set_context = Mock()
        mock.structured_logger.clear_context = Mock()
        mock.structured_logger.info = Mock()
        mock.structured_logger.warning = Mock()
        mock.structured_logger.error = Mock()
        mock.structured_logger.audit_user_action = Mock()
        mock.structured_logger.audit_security_event = Mock()

        # Mock performance timing context manager
        context_manager = Mock()
        context_manager.__enter__ = Mock()
        context_manager.__exit__ = Mock()
        mock.structured_logger.performance_timing = Mock(return_value=context_manager)

        # Mock use cases
        mock.detect_controllers_use_case = Mock()
        mock.setup_controller_use_case = Mock()
        mock.install_emulator_use_case = Mock()
        mock.list_roms_use_case = Mock()
        mock.update_system_use_case = Mock()

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
    def gaming_system_tools(self, mock_container: Mock) -> GamingSystemTools:
        """Provide GamingSystemTools instance with mocked dependencies."""
        return GamingSystemTools(mock_container)

    @pytest.mark.asyncio
    async def test_handle_tool_call_sets_logging_context(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that handle_tool_call sets up proper logging context."""
        # Mock successful controller detection
        mock_result = Mock()
        mock_result.is_error.return_value = False
        mock_result.value = []
        mock_container.detect_controllers_use_case.execute.return_value = mock_result

        arguments = {"component": "controller", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify correlation ID was generated
        mock_container.structured_logger.generate_correlation_id.assert_called_once()

        # Verify context was set with proper values
        mock_container.structured_logger.set_context.assert_called_once()
        context_call = mock_container.structured_logger.set_context.call_args[0][0]

        assert context_call.correlation_id == "test-correlation-123"
        assert context_call.username == "retro"
        assert context_call.component == "controller"
        assert context_call.action == "detect"

    @pytest.mark.asyncio
    async def test_handle_tool_call_clears_context_on_completion(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that handle_tool_call clears context after completion."""
        # Mock successful controller detection
        mock_result = Mock()
        mock_result.is_error.return_value = False
        mock_result.value = []
        mock_container.detect_controllers_use_case.execute.return_value = mock_result

        arguments = {"component": "controller", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify context was cleared
        mock_container.structured_logger.clear_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_user_action_logged_for_successful_operation(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that successful operations log audit events."""
        # Mock successful controller detection
        from retromcp.domain.models import Controller
        from retromcp.domain.models import ControllerType

        controller = Controller(
            name="Xbox Controller",
            device_path="/dev/input/js0",
            controller_type=ControllerType.XBOX,
            connected=True,
        )
        mock_result = Mock()
        mock_result.is_error.return_value = False
        mock_result.value = [controller]
        mock_container.detect_controllers_use_case.execute.return_value = mock_result

        arguments = {"component": "controller", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify audit event was logged
        mock_container.structured_logger.audit_user_action.assert_called_once()
        audit_call = mock_container.structured_logger.audit_user_action.call_args[0][0]

        assert audit_call.action == "controller_detect"
        assert audit_call.target == "controller"
        assert audit_call.success is True
        assert "controllers_found" in audit_call.details

    @pytest.mark.asyncio
    async def test_security_event_logged_for_invalid_component(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that invalid components trigger security event logging."""
        arguments = {"component": "../../etc/passwd", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify security event was logged
        mock_container.structured_logger.audit_security_event.assert_called_once()
        security_call = mock_container.structured_logger.audit_security_event.call_args

        assert "Invalid component" in security_call[0][0]  # message
        assert security_call[1]["blocked_action"] == "manage_gaming"
        assert security_call[1]["reason"] == "invalid_component"

    @pytest.mark.asyncio
    async def test_error_categorization_for_validation_errors(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that validation errors are properly categorized."""
        arguments = {
            "action": "detect"  # Missing component
        }

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify error was logged with proper categorization
        mock_container.structured_logger.error.assert_called()
        error_call = mock_container.structured_logger.error.call_args

        assert "Component is required" in error_call[0][0]  # message
        assert error_call[1]["category"] == ErrorCategory.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_performance_timing_for_long_operations(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that long operations are timed for performance monitoring."""
        # Mock a successful but potentially slow operation (system update)
        command_result = CommandResult(
            command="sudo apt update",
            success=True,
            stdout="Updated package lists",
            stderr="",
            exit_code=0,
            execution_time=5.5,
        )
        mock_result = Mock()
        mock_result.is_error.return_value = False
        mock_result.value = command_result
        mock_container.update_system_use_case.execute.return_value = mock_result

        # Mock performance timing context manager
        mock_container.structured_logger.performance_timing.return_value.__enter__ = (
            Mock()
        )
        mock_container.structured_logger.performance_timing.return_value.__exit__ = (
            Mock()
        )

        arguments = {"component": "retropie", "action": "setup", "target": "update"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify performance timing was used
        mock_container.structured_logger.performance_timing.assert_called_with(
            "retropie_setup_update"
        )

    @pytest.mark.asyncio
    async def test_info_logging_for_operation_start(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that operations log start events with context."""
        # Mock successful controller detection
        mock_result = Mock()
        mock_result.is_error.return_value = False
        mock_result.value = []
        mock_container.detect_controllers_use_case.execute.return_value = mock_result

        arguments = {"component": "controller", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Verify info logging was called for operation start
        mock_container.structured_logger.info.assert_called()
        info_calls = mock_container.structured_logger.info.call_args_list

        # Should have at least one call for operation start
        assert len(info_calls) >= 1
        start_call = info_calls[0]
        assert "Starting" in start_call[0][0] or "Executing" in start_call[0][0]

    @pytest.mark.asyncio
    async def test_warning_logging_for_non_critical_errors(
        self, gaming_system_tools: GamingSystemTools, mock_container: Mock
    ) -> None:
        """Test that non-critical errors are logged as warnings."""
        # Mock a use case that returns error result
        from retromcp.domain.models import DomainError

        error = DomainError("Controller not found", "CONTROLLER_NOT_FOUND")
        mock_result = Mock()
        mock_result.is_error.return_value = True
        mock_result.error_or_none = error
        mock_container.detect_controllers_use_case.execute.return_value = mock_result

        arguments = {"component": "controller", "action": "detect"}

        # Execute the tool call
        await gaming_system_tools.handle_tool_call("manage_gaming", arguments)

        # Should log error appropriately
        mock_container.structured_logger.error.assert_called()
        error_call = mock_container.structured_logger.error.call_args

        assert "Controller detection failed" in error_call[0][0]
        assert error_call[1]["category"] == ErrorCategory.SYSTEM_ERROR
