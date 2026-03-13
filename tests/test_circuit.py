"""Tests for CircuitBreaker."""

import time

import pytest

from apiguard.circuit import CircuitBreaker, CircuitState
from apiguard.exceptions import CircuitOpenError


class TestCircuitBreaker:
    """Test suite for CircuitBreaker."""

    def test_initial_state_closed(self) -> None:
        """Circuit starts in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed() is True
        assert breaker.is_open() is False

    def test_success_no_failure_count(self) -> None:
        """Successful calls don't increment failure count."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

        for _ in range(3):
            with breaker:
                pass

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_failures_open_circuit(self) -> None:
        """Exceeding failure threshold opens circuit."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        for _ in range(3):
            try:
                with breaker:
                    raise ValueError("error")
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open() is True

    def test_open_circuit_rejects_requests(self) -> None:
        """OPEN circuit raises CircuitOpenError."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

        # Trigger failure to open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        assert breaker.is_open() is True

        # Next call should fail fast
        with pytest.raises(CircuitOpenError, match="Circuit breaker is OPEN"), breaker:
            pass

    def test_recovery_timeout_transitions_to_half_open(self) -> None:
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        assert breaker.is_open() is True

        # Wait for recovery timeout
        time.sleep(0.15)

        # Check state transitions to HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.is_half_open() is True

    def test_half_open_success_closes_circuit(self) -> None:
        """Successful call in HALF_OPEN closes circuit."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Successful call closes circuit
        with breaker:
            pass

        assert breaker.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self) -> None:
        """Failed call in HALF_OPEN reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Failed call reopens circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN

    def test_success_threshold_in_half_open(self) -> None:
        """Multiple successes required in HALF_OPEN to close."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=3,
        )

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN

        # Need 3 successes to close
        with breaker:
            pass
        assert breaker.state == CircuitState.HALF_OPEN

        with breaker:
            pass
        assert breaker.state == CircuitState.HALF_OPEN

        with breaker:
            pass
        assert breaker.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        """Reset returns circuit to CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        assert breaker.is_open() is True

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_invalid_failure_threshold(self) -> None:
        """Non-positive failure threshold raises error."""
        with pytest.raises(ValueError, match="positive"):
            CircuitBreaker(failure_threshold=0, recovery_timeout=60.0)
        with pytest.raises(ValueError, match="positive"):
            CircuitBreaker(failure_threshold=-1, recovery_timeout=60.0)

    def test_invalid_recovery_timeout(self) -> None:
        """Non-positive recovery timeout raises error."""
        with pytest.raises(ValueError, match="positive"):
            CircuitBreaker(failure_threshold=5, recovery_timeout=0.0)
        with pytest.raises(ValueError, match="positive"):
            CircuitBreaker(failure_threshold=5, recovery_timeout=-1.0)

    def test_invalid_success_threshold(self) -> None:
        """Non-positive success threshold raises error."""
        with pytest.raises(ValueError, match="positive"):
            CircuitBreaker(failure_threshold=5, recovery_timeout=60.0, success_threshold=0)

    def test_thread_safety(self) -> None:
        """Circuit breaker is thread-safe."""
        import threading

        breaker = CircuitBreaker(failure_threshold=1000, recovery_timeout=60.0)
        success_count = [0]
        failure_count = [0]
        lock = threading.Lock()

        def successful_calls() -> None:
            for _ in range(100):
                try:
                    with breaker, lock:
                        success_count[0] += 1
                except CircuitOpenError:
                    pass

        def failed_calls() -> None:
            for _ in range(100):
                try:
                    with breaker:
                        raise ValueError("error")
                except (ValueError, CircuitOpenError):
                    with lock:
                        failure_count[0] += 1

        threads = [
            threading.Thread(target=successful_calls) for _ in range(5)
        ] + [
            threading.Thread(target=failed_calls) for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Circuit should not be open (threshold high enough for 500 failures)
        assert success_count[0] == 500
        assert failure_count[0] == 500

    def test_circuit_open_error_recovery_timeout(self) -> None:
        """CircuitOpenError includes recovery_timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)

        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        with pytest.raises(CircuitOpenError) as exc_info, breaker:
            pass

        assert exc_info.value.recovery_timeout == 30.0