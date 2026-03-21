"""Tests for exceptions."""

from apiguard.exceptions import CircuitOpenError, RetryExhaustedError


class TestCircuitOpenError:
    """Test suite for CircuitOpenError."""

    def test_default_message(self) -> None:
        """CircuitOpenError has default message."""
        error = CircuitOpenError()
        assert str(error) == "Circuit breaker is OPEN"

    def test_custom_message(self) -> None:
        """CircuitOpenError accepts custom message."""
        error = CircuitOpenError("Custom message")
        assert str(error) == "Custom message"

    def test_recovery_timeout(self) -> None:
        """CircuitOpenError stores recovery_timeout."""
        error = CircuitOpenError(recovery_timeout=60.0)
        assert error.recovery_timeout == 60.0

    def test_message_and_timeout(self) -> None:
        """CircuitOpenError accepts both message and timeout."""
        error = CircuitOpenError("Circuit open", recovery_timeout=30.0)
        assert str(error) == "Circuit open"
        assert error.recovery_timeout == 30.0


class TestRetryExhaustedError:
    """Test suite for RetryExhaustedError."""

    def test_default_message(self) -> None:
        """RetryExhaustedError has default message."""
        error = RetryExhaustedError()
        assert str(error) == "All retry attempts exhausted"

    def test_custom_message(self) -> None:
        """RetryExhaustedError accepts custom message."""
        error = RetryExhaustedError("Custom message")
        assert str(error) == "Custom message"

    def test_attempts(self) -> None:
        """RetryExhaustedError stores attempts."""
        error = RetryExhaustedError(attempts=3)
        assert error.attempts == 3

    def test_last_error(self) -> None:
        """RetryExhaustedError stores last_error."""
        original_error = ValueError("original")
        error = RetryExhaustedError(last_error=original_error)
        assert error.last_error is original_error

    def test_all_parameters(self) -> None:
        """RetryExhaustedError accepts all parameters."""
        original_error = ValueError("original")
        error = RetryExhaustedError(
            "Failed after retries",
            attempts=5,
            last_error=original_error,
        )
        assert str(error) == "Failed after retries"
        assert error.attempts == 5
        assert error.last_error is original_error
