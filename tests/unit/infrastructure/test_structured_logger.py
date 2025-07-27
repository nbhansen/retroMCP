"""Unit tests for structured logging utility."""

import json
import logging
from unittest.mock import Mock
from unittest.mock import patch
from uuid import UUID

import pytest

from retromcp.infrastructure.structured_logger import AuditEvent
from retromcp.infrastructure.structured_logger import ErrorCategory
from retromcp.infrastructure.structured_logger import LogContext
from retromcp.infrastructure.structured_logger import StructuredLogger


@pytest.mark.unit
@pytest.mark.infrastructure
class TestStructuredLogger:
    """Test cases for StructuredLogger class."""

    @pytest.fixture
    def mock_logger(self) -> Mock:
        """Provide mocked logger."""
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def structured_logger(self, mock_logger: Mock) -> StructuredLogger:
        """Provide StructuredLogger instance with mocked logger."""
        return StructuredLogger(mock_logger)

    def test_structured_logger_initialization(self, mock_logger: Mock) -> None:
        """Test StructuredLogger initializes correctly."""
        logger = StructuredLogger(mock_logger)
        assert logger._logger == mock_logger
        assert logger._context == {}

    def test_set_context_stores_user_context(
        self, structured_logger: StructuredLogger
    ) -> None:
        """Test that set_context stores user context correctly."""
        context = LogContext(
            correlation_id="test-123",
            username="retro",
            component="controller",
            action="setup",
        )

        structured_logger.set_context(context)

        assert structured_logger._context["correlation_id"] == "test-123"
        assert structured_logger._context["username"] == "retro"
        assert structured_logger._context["component"] == "controller"
        assert structured_logger._context["action"] == "setup"

    def test_clear_context_removes_stored_context(
        self, structured_logger: StructuredLogger
    ) -> None:
        """Test that clear_context removes all stored context."""
        context = LogContext(
            correlation_id="test-123",
            username="retro",
            component="controller",
            action="setup",
        )
        structured_logger.set_context(context)

        structured_logger.clear_context()

        assert structured_logger._context == {}

    def test_generate_correlation_id_returns_valid_uuid(
        self, structured_logger: StructuredLogger
    ) -> None:
        """Test that generate_correlation_id returns valid UUID string."""
        correlation_id = structured_logger.generate_correlation_id()

        # Should be able to parse as UUID
        uuid_obj = UUID(correlation_id)
        assert str(uuid_obj) == correlation_id

    def test_info_with_context_logs_structured_message(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that info logs include context and structured data."""
        context = LogContext(
            correlation_id="test-123",
            username="retro",
            component="controller",
            action="setup",
        )
        structured_logger.set_context(context)

        structured_logger.info(
            "Controller setup started", extra_data={"controller_type": "xbox"}
        )

        # Verify log was called
        mock_logger.info.assert_called_once()

        # Extract the logged message and verify it's valid JSON
        logged_message = mock_logger.info.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["message"] == "Controller setup started"
        assert log_data["level"] == "INFO"
        assert log_data["correlation_id"] == "test-123"
        assert log_data["username"] == "retro"
        assert log_data["component"] == "controller"
        assert log_data["action"] == "setup"
        assert log_data["controller_type"] == "xbox"
        assert "timestamp" in log_data

    def test_warning_with_context_logs_structured_message(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that warning logs include context and structured data."""
        context = LogContext(
            correlation_id="test-456",
            username="retro",
            component="emulator",
            action="install",
        )
        structured_logger.set_context(context)

        structured_logger.warning("Emulator installation taking longer than expected")

        mock_logger.warning.assert_called_once()
        logged_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(logged_message)

        assert (
            log_data["message"] == "Emulator installation taking longer than expected"
        )
        assert log_data["level"] == "WARNING"
        assert log_data["correlation_id"] == "test-456"

    def test_error_with_categorization_logs_structured_message(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that error logs include categorization and context."""
        context = LogContext(
            correlation_id="test-789", username="retro", component="roms", action="scan"
        )
        structured_logger.set_context(context)

        structured_logger.error(
            "Failed to access ROM directory",
            category=ErrorCategory.PERMISSION_DENIED,
            extra_data={"path": "/home/retro/RetroPie/roms"},
        )

        mock_logger.error.assert_called_once()
        logged_message = mock_logger.error.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["message"] == "Failed to access ROM directory"
        assert log_data["level"] == "ERROR"
        assert log_data["error_category"] == "PERMISSION_DENIED"
        assert log_data["path"] == "/home/retro/RetroPie/roms"

    def test_audit_user_action_logs_audit_event(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that audit_user_action logs user actions with audit context."""
        context = LogContext(
            correlation_id="audit-123",
            username="retro",
            component="controller",
            action="setup",
        )
        structured_logger.set_context(context)

        event = AuditEvent(
            action="controller_setup",
            target="xbox",
            success=True,
            details={"controller_type": "xbox", "device_path": "/dev/input/js0"},
        )

        structured_logger.audit_user_action(event)

        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["event_type"] == "USER_ACTION_AUDIT"
        assert log_data["action"] == "controller_setup"
        assert log_data["target"] == "xbox"
        assert log_data["success"] is True
        assert log_data["controller_type"] == "xbox"
        assert log_data["device_path"] == "/dev/input/js0"

    def test_audit_security_event_logs_security_context(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that audit_security_event logs security events appropriately."""
        context = LogContext(
            correlation_id="security-456",
            username="retro",
            component="roms",
            action="configure",
        )
        structured_logger.set_context(context)

        structured_logger.audit_security_event(
            "Invalid target specified for ROM configuration",
            blocked_action="configure_roms",
            reason="invalid_target",
            extra_data={"requested_target": "../../etc/passwd"},
        )

        mock_logger.warning.assert_called_once()
        logged_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["event_type"] == "SECURITY_EVENT"
        assert log_data["message"] == "Invalid target specified for ROM configuration"
        assert log_data["blocked_action"] == "configure_roms"
        assert log_data["reason"] == "invalid_target"
        assert log_data["requested_target"] == "../../etc/passwd"

    @patch("retromcp.infrastructure.structured_logger.time.time")
    def test_performance_timing_context_manager(
        self, mock_time: Mock, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that performance timing context manager logs execution time."""
        mock_time.side_effect = [
            1000.0,
            1005.5,
            1010.0,
        ]  # Extra call for _build_log_data

        context = LogContext(
            correlation_id="perf-123",
            username="retro",
            component="emulator",
            action="install",
        )
        structured_logger.set_context(context)

        with structured_logger.performance_timing("emulator_installation"):
            pass  # Simulate some work

        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["event_type"] == "PERFORMANCE_TIMING"
        assert log_data["operation"] == "emulator_installation"
        assert log_data["duration_seconds"] == 5.5

    def test_log_without_context_still_works(
        self, structured_logger: StructuredLogger, mock_logger: Mock
    ) -> None:
        """Test that logging works even without set context."""
        structured_logger.info("Test message without context")

        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        log_data = json.loads(logged_message)

        assert log_data["message"] == "Test message without context"
        assert log_data["level"] == "INFO"
        assert "timestamp" in log_data
        # Context fields should not be present or be None
        assert log_data.get("correlation_id") is None
        assert log_data.get("username") is None

    def test_error_category_enum_values(self) -> None:
        """Test that ErrorCategory enum has expected values."""
        assert ErrorCategory.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCategory.PERMISSION_DENIED.value == "PERMISSION_DENIED"
        assert ErrorCategory.COMMAND_EXECUTION_ERROR.value == "COMMAND_EXECUTION_ERROR"
        assert ErrorCategory.CONNECTION_ERROR.value == "CONNECTION_ERROR"
        assert ErrorCategory.CONFIGURATION_ERROR.value == "CONFIGURATION_ERROR"
        assert ErrorCategory.RESOURCE_NOT_FOUND.value == "RESOURCE_NOT_FOUND"
        assert ErrorCategory.SYSTEM_ERROR.value == "SYSTEM_ERROR"

    def test_log_context_dataclass(self) -> None:
        """Test LogContext dataclass initialization and fields."""
        context = LogContext(
            correlation_id="test-123",
            username="retro",
            component="controller",
            action="setup",
        )

        assert context.correlation_id == "test-123"
        assert context.username == "retro"
        assert context.component == "controller"
        assert context.action == "setup"

    def test_audit_event_dataclass(self) -> None:
        """Test AuditEvent dataclass initialization and fields."""
        event = AuditEvent(
            action="controller_setup",
            target="xbox",
            success=True,
            details={"test": "data"},
        )

        assert event.action == "controller_setup"
        assert event.target == "xbox"
        assert event.success is True
        assert event.details == {"test": "data"}
