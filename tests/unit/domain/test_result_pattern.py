"""Tests for unified Result pattern and domain error hierarchy.

Following TDD approach - these tests will initially fail until Result implementation is created.
"""

import pytest

# Import will fail initially - part of TDD Red phase
try:
    from retromcp.domain.models import ConnectionError
    from retromcp.domain.models import DomainError
    from retromcp.domain.models import ExecutionError
    from retromcp.domain.models import Result
    from retromcp.domain.models import ValidationError
except ImportError:
    # Expected during Red phase of TDD
    pass


class TestResult:
    """Test unified Result pattern implementation."""

    def test_result_success_creation(self):
        """Test creating successful Result instances."""
        # Arrange & Act
        result = Result.success("test_value")

        # Assert
        assert result.is_success()
        assert not result.is_error()
        assert result.value == "test_value"

    def test_result_error_creation(self):
        """Test creating error Result instances."""
        # Arrange
        error = DomainError(code="TEST_ERROR", message="Test error message")

        # Act
        result = Result.error(error)

        # Assert
        assert not result.is_success()
        assert result.is_error()
        assert result.error_value.code == "TEST_ERROR"
        assert result.error_value.message == "Test error message"

    def test_result_success_value_access(self):
        """Test accessing value from successful Result."""
        # Arrange
        result = Result.success(42)

        # Act & Assert
        assert result.value == 42

    def test_result_error_value_access(self):
        """Test accessing error from failed Result."""
        # Arrange
        error = DomainError(code="ERR", message="Error")
        result = Result.error(error)

        # Act & Assert
        assert result.error_value == error

    def test_result_success_value_access_from_error_raises(self):
        """Test that accessing value from error Result raises ValueError."""
        # Arrange
        error = DomainError(code="ERR", message="Error")
        result = Result.error(error)

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot get value from error result"):
            _ = result.success_value

    def test_result_error_value_access_from_success_raises(self):
        """Test that accessing error from success Result raises ValueError."""
        # Arrange
        result = Result.success("success")

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot get error from success result"):
            _ = result.error_value

    def test_result_immutability(self):
        """Test that Result instances are immutable."""
        # Arrange
        result = Result.success("value")

        # Act & Assert - should not be able to modify
        with pytest.raises(AttributeError):
            result._value = "new_value"

    def test_result_with_complex_types(self):
        """Test Result with complex success and error types."""
        # Arrange
        success_data = {"key": "value", "count": 42}
        error_data = ValidationError(
            code="VALIDATION_FAILED",
            message="Input validation failed",
            details={"field": "username", "reason": "too_short"},
        )

        # Act
        success_result = Result.success(success_data)
        error_result = Result.error(error_data)

        # Assert
        assert success_result.value == success_data
        assert error_result.error_value.details["field"] == "username"


class TestDomainError:
    """Test domain error hierarchy."""

    def test_domain_error_creation(self):
        """Test creating base DomainError instances."""
        # Arrange & Act
        error = DomainError(
            code="GENERIC_ERROR",
            message="Something went wrong",
            details={"context": "test"},
        )

        # Assert
        assert error.code == "GENERIC_ERROR"
        assert error.message == "Something went wrong"
        assert error.details["context"] == "test"

    def test_domain_error_without_details(self):
        """Test creating DomainError without details."""
        # Arrange & Act
        error = DomainError(code="SIMPLE_ERROR", message="Simple error")

        # Assert
        assert error.code == "SIMPLE_ERROR"
        assert error.message == "Simple error"
        assert error.details is None

    def test_domain_error_immutability(self):
        """Test that DomainError instances are immutable."""
        # Arrange
        error = DomainError(code="ERR", message="Error")

        # Act & Assert - should not be able to modify
        with pytest.raises(AttributeError):
            error.code = "NEW_ERR"


class TestValidationError:
    """Test ValidationError specific functionality."""

    def test_validation_error_creation(self):
        """Test creating ValidationError instances."""
        # Arrange & Act
        error = ValidationError(
            code="INVALID_INPUT",
            message="Invalid input provided",
            details={"field": "email", "value": "invalid-email"},
        )

        # Assert
        assert isinstance(error, DomainError)
        assert error.code == "INVALID_INPUT"
        assert error.message == "Invalid input provided"
        assert error.details["field"] == "email"

    def test_validation_error_in_result(self):
        """Test using ValidationError in Result pattern."""
        # Arrange
        error = ValidationError(code="VAL_ERR", message="Validation failed")

        # Act
        result = Result.error(error)

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "VAL_ERR"


class TestConnectionError:
    """Test ConnectionError specific functionality."""

    def test_connection_error_creation(self):
        """Test creating ConnectionError instances."""
        # Arrange & Act
        error = ConnectionError(
            code="SSH_FAILED",
            message="SSH connection failed",
            details={"host": "retropie.local", "port": 22},
        )

        # Assert
        assert isinstance(error, DomainError)
        assert error.code == "SSH_FAILED"
        assert error.message == "SSH connection failed"
        assert error.details["host"] == "retropie.local"

    def test_connection_error_in_result(self):
        """Test using ConnectionError in Result pattern."""
        # Arrange
        error = ConnectionError(code="CONN_ERR", message="Connection failed")

        # Act
        result = Result.error(error)

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ConnectionError)


class TestExecutionError:
    """Test ExecutionError specific functionality."""

    def test_execution_error_creation(self):
        """Test creating ExecutionError instances."""
        # Arrange & Act
        error = ExecutionError(
            code="COMMAND_FAILED",
            message="Command execution failed",
            command="sudo systemctl restart retropie",
            exit_code=1,
            stderr="systemctl: command not found",
        )

        # Assert
        assert error.code == "COMMAND_FAILED"
        assert error.message == "Command execution failed"
        assert error.command == "sudo systemctl restart retropie"
        assert error.exit_code == 1
        assert error.stderr == "systemctl: command not found"

    def test_execution_error_in_result(self):
        """Test using ExecutionError in Result pattern."""
        # Arrange
        error = ExecutionError(
            code="EXEC_ERR",
            message="Execution failed",
            command="test",
            exit_code=1,
            stderr="error",
        )

        # Act
        result = Result.error(error)

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ExecutionError)
        assert result.error_value.command == "test"
        assert result.error_value.exit_code == 1
