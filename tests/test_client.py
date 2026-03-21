"""Tests for RateLimitedClient."""

import pytest

from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker
from apiguard.client import RateLimitedClient
from apiguard.exceptions import CircuitOpenError
from apiguard.retry import RetryHandler


class TestRateLimitedClient:
    """Test suite for RateLimitedClient."""

    def test_composition(self) -> None:
        """Client composes bucket, retry, and breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        retry = RetryHandler(max_retries=3)
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

        client = RateLimitedClient(bucket=bucket, retry=retry, breaker=breaker)

        assert client.bucket is bucket
        assert client.retry is retry
        assert client.breaker is breaker

    def test_minimal_client(self) -> None:
        """Client can be created with only bucket."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = RateLimitedClient(bucket=bucket)

        assert client.bucket is bucket
        assert client.retry is None
        assert client.breaker is None

    def test_acquire_tokens(self) -> None:
        """Client can acquire tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = RateLimitedClient(bucket=bucket)

        assert client.acquire(10) is True
        assert client.available() == pytest.approx(90.0, abs=0.1)

    def test_available_tokens(self) -> None:
        """Client returns available tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = RateLimitedClient(bucket=bucket)

        assert client.available() == 100.0

    def test_context_manager_no_breaker(self) -> None:
        """Context manager works without circuit breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = RateLimitedClient(bucket=bucket)

        with client:
            pass  # No-op, should not raise

    def test_context_manager_with_breaker(self) -> None:
        """Context manager delegates to circuit breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        client = RateLimitedClient(bucket=bucket, breaker=breaker)

        with client:
            pass

        assert breaker.is_closed() is True

    def test_context_manager_open_circuit(self) -> None:
        """Context manager raises CircuitOpenError if circuit open."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        client = RateLimitedClient(bucket=bucket, breaker=breaker)

        # Open circuit
        try:
            with client:
                raise ValueError("error")
        except ValueError:
            pass

        with pytest.raises(CircuitOpenError), client:
            pass

    def test_check_circuit(self) -> None:
        """check_circuit raises CircuitOpenError if open."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        client = RateLimitedClient(bucket=bucket, breaker=breaker)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        with pytest.raises(CircuitOpenError):
            client.check_circuit()

    def test_check_circuit_no_breaker(self) -> None:
        """check_circuit does nothing if no breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = RateLimitedClient(bucket=bucket)

        # Should not raise
        client.check_circuit()

    def test_client_records_success(self) -> None:
        """Successful context manager records success on breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        client = RateLimitedClient(bucket=bucket, breaker=breaker)

        # Open circuit
        try:
            with client:
                raise ValueError("error")
        except ValueError:
            pass

        assert breaker.is_open() is True

        # Reset breaker
        breaker.reset()

        # Successful call
        with client:
            pass

        assert breaker.is_closed() is True
