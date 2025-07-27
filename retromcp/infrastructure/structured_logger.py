"""Structured logging utility for retroMCP."""

import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categorization for structured logging."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


@dataclass(frozen=True)
class LogContext:
    """Context information for structured logging."""

    correlation_id: str
    username: Optional[str] = None
    component: Optional[str] = None
    action: Optional[str] = None


@dataclass(frozen=True)
class AuditEvent:
    """Audit event for user action tracking."""

    action: str
    target: Optional[str] = None
    success: bool = True
    details: Optional[Dict[str, Any]] = None


class StructuredLogger:
    """Provides structured logging with correlation IDs and user context."""

    def __init__(self, component: str, correlation_id: Optional[str] = None) -> None:
        """Initialize structured logger for a component.

        Args:
            component: Name of the component (e.g., 'gaming_tools', 'ssh_client')
            correlation_id: Optional correlation ID for tracking requests
        """
        self.component = component
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"retromcp.{component}")
        self._context: Dict[str, Any] = {}

    def _format_message(self, message: str, **kwargs: Any) -> str:
        """Format log message with structured context."""
        context = {
            "component": self.component,
            "correlation_id": self.correlation_id,
            **kwargs,
        }

        context_str = " ".join(f"{k}={v}" for k, v in context.items() if v is not None)
        return f"[{context_str}] {message}"

    def audit_user_action(
        self,
        action: str,
        target: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log user action for audit trail."""
        message = f"User action: {action}"
        if target:
            message += f" on {target}"

        context = {
            "action_type": "user_action",
            "action": action,
            "target": target,
            **(user_context or {}),
            **kwargs,
        }

        self.logger.info(self._format_message(message, **context))

    def performance_start(self, operation: str, **kwargs: Any) -> str:
        """Start performance tracking for an operation."""
        operation_id = str(uuid.uuid4())[:8]
        context = {
            "action_type": "performance_start",
            "operation": operation,
            "operation_id": operation_id,
            "start_time": time.time(),
            **kwargs,
        }

        self.logger.debug(
            self._format_message(f"Starting operation: {operation}", **context)
        )
        return operation_id

    def performance_end(
        self,
        operation: str,
        operation_id: str,
        start_time: float,
        success: bool = True,
        **kwargs: Any,
    ) -> None:
        """End performance tracking for an operation."""
        duration = time.time() - start_time
        context = {
            "action_type": "performance_end",
            "operation": operation,
            "operation_id": operation_id,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            **kwargs,
        }

        level = logging.INFO if success else logging.WARNING
        status = "completed" if success else "failed"
        message = f"Operation {status}: {operation} (took {duration:.2f}s)"

        self.logger.log(level, self._format_message(message, **context))

    def security_event(
        self, event_type: str, details: str, severity: str = "medium", **kwargs: Any
    ) -> None:
        """Log security events like blocked commands or validation failures."""
        context = {
            "action_type": "security_event",
            "event_type": event_type,
            "severity": severity,
            **kwargs,
        }

        level = logging.ERROR if severity == "high" else logging.WARNING
        message = f"Security event ({event_type}): {details}"

        self.logger.log(level, self._format_message(message, **context))

    def error_with_context(
        self,
        error_message: str,
        error_type: str = "general",
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Log errors with structured context."""
        context = {
            "action_type": "error",
            "error_type": error_type,
            "command": command,
            "exit_code": exit_code,
            **kwargs,
        }

        self.logger.error(self._format_message(f"Error: {error_message}", **context))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        context = {"action_type": "info", **kwargs}
        self.logger.info(self._format_message(message, **context))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        context = {"action_type": "warning", **kwargs}
        self.logger.warning(self._format_message(message, **context))

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        context = {"action_type": "debug", **kwargs}
        self.logger.debug(self._format_message(message, **context))

    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())

    def set_context(self, context: LogContext) -> None:
        """Set logging context."""
        self._context = {
            "correlation_id": context.correlation_id,
            "username": context.username,
            "component": context.component,
            "action": context.action,
        }

    def clear_context(self) -> None:
        """Clear logging context."""
        self._context = {}

    def audit_security_event(self, message: str, **kwargs: Any) -> None:
        """Log security audit event."""
        self.security_event("security_audit", message, **kwargs)

    def error(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
        **kwargs: Any,
    ) -> None:
        """Log error with category."""
        context = {"action_type": "error", "error_category": category.value, **kwargs}
        self.logger.error(self._format_message(message, **context))

    def performance_timing(self, operation: str) -> "PerformanceTimer":
        """Context manager for performance timing."""
        return PerformanceTimer(self, operation)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, logger: StructuredLogger, operation: str) -> None:
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self) -> "PerformanceTimer":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.info(
                f"Performance timing: {self.operation}",
                event_type="PERFORMANCE_TIMING",
                operation=self.operation,
                duration_seconds=duration,
            )
