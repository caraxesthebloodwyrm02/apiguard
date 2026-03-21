"""Tests for RetryHandler."""

import pytest

from apiguard.retry import RetryHandler


class TestRetryHandler:
    """Test suite for RetryHandler."""

    @pytest.mark.asyncio
    async def test_attempts_generator(self) -> None:
        """Attempts generator yields correct sequence."""
        retry = RetryHandler(max_retries=3)
        attempts = []
        async for a in retry.attempts():
            attempts.append(a)
        assert attempts == [0, 1, 2, 3]

    def test_backoff_calculation(self) -> None:
        """Exponential backoff is calculated correctly."""
        retry = RetryHandler(max_retries=5, base_delay=1.0, jitter=0.0)

        # Attempt 1: 1.0 * 2^0 = 1.0
        assert retry._calculate_backoff(1) == 1.0
        # Attempt 2: 1.0 * 2^1 = 2.0
        assert retry._calculate_backoff(2) == 2.0
        # Attempt 3: 1.0 * 2^2 = 4.0
        assert retry._calculate_backoff(3) == 4.0
        # Attempt 4: 1.0 * 2^3 = 8.0
        assert retry._calculate_backoff(4) == 8.0

    def test_backoff_with_max_delay(self) -> None:
        """Backoff is capped at max_delay."""
        retry = RetryHandler(max_retries=10, base_delay=1.0, max_delay=10.0, jitter=0.0)
        assert retry._calculate_backoff(5) == 10.0  # Would be 16, capped at 10
        assert retry._calculate_backoff(10) == 10.0

    def test_jitter_adds_randomness(self) -> None:
        """Jitter adds randomness to backoff."""
        retry = RetryHandler(max_retries=5, base_delay=1.0, jitter=0.5)

        # Run multiple times to check for variance
        delays = [retry._calculate_backoff(1) for _ in range(100)]

        # With 0.5 jitter, delays should vary between 0.5 and 1.5
        assert min(delays) < 1.0
        assert max(delays) > 1.0
        # All delays should be within [0.5, 1.5]
        for d in delays:
            assert 0.5 <= d <= 1.5

    def test_retry_after_header(self) -> None:
        """Retry-After header is extracted from response."""
        import httpx

        retry = RetryHandler(max_retries=3)

        # Response with Retry-After header
        response = httpx.Response(status_code=429, headers={"Retry-After": "5"})
        assert retry._get_retry_after(response) == 5.0

        # Response without header
        response = httpx.Response(status_code=500)
        assert retry._get_retry_after(response) is None

    def test_retryable_status_codes(self) -> None:
        """Default retryable status codes."""
        retry = RetryHandler(max_retries=3)

        assert retry.is_retryable(429) is True
        assert retry.is_retryable(500) is True
        assert retry.is_retryable(502) is True
        assert retry.is_retryable(503) is True
        assert retry.is_retryable(504) is True
        assert retry.is_retryable(200) is False
        assert retry.is_retryable(404) is False

    def test_custom_retryable_codes(self) -> None:
        """Custom retryable status codes."""
        retry = RetryHandler(max_retries=3, retryable_status_codes={408, 409})

        assert retry.is_retryable(408) is True
        assert retry.is_retryable(409) is True
        assert retry.is_retryable(500) is False

    def test_invalid_max_retries(self) -> None:
        """Negative max_retries raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            RetryHandler(max_retries=-1)

    def test_invalid_base_delay(self) -> None:
        """Non-positive base_delay raises error."""
        with pytest.raises(ValueError, match="positive"):
            RetryHandler(max_retries=3, base_delay=0.0)
        with pytest.raises(ValueError, match="positive"):
            RetryHandler(max_retries=3, base_delay=-1.0)

    def test_invalid_max_delay(self) -> None:
        """Non-positive max_delay raises error."""
        with pytest.raises(ValueError, match="positive"):
            RetryHandler(max_retries=3, max_delay=0.0)

    def test_invalid_jitter(self) -> None:
        """Jitter outside [0, 1] raises error."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            RetryHandler(max_retries=3, jitter=-0.1)
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            RetryHandler(max_retries=3, jitter=1.5)

    @pytest.mark.asyncio
    async def test_apply_backoff(self) -> None:
        """Apply backoff with delay."""
        retry = RetryHandler(max_retries=3, base_delay=0.1, jitter=0.0)

        import time

        start = time.monotonic()
        await retry.apply_backoff(1)
        elapsed = time.monotonic() - start

        # Should have delayed approximately 0.1 seconds
        assert 0.09 < elapsed < 0.15

    def test_retry_after_http_date_returns_none(self) -> None:
        """Non-numeric Retry-After (HTTP-date) returns None."""
        import httpx

        retry = RetryHandler(max_retries=3)
        response = httpx.Response(
            status_code=429,
            headers={"Retry-After": "Thu, 01 Jan 2026 00:00:00 GMT"},
        )
        assert retry._get_retry_after(response) is None
