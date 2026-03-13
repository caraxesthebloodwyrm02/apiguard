"""Retry handler with exponential backoff and jitter."""

import asyncio
import random
from collections.abc import AsyncIterator

import httpx


class RetryHandler:
    """Retry handler with exponential backoff, jitter, and Retry-After support.

    Example:
        retry = RetryHandler(max_retries=3, base_delay=1.0)
        async for attempt in retry.attempts():
            response = await client.get(url)
            if response.status_code == 200:
                break
            await retry.apply_backoff(attempt, response)
    """

    def __init__(
        self,
        max_retries: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: float = 0.1,
        retryable_status_codes: set[int] | None = None,
    ) -> None:
        """Initialize the retry handler.

        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay in seconds for exponential backoff.
            max_delay: Maximum delay cap in seconds.
            jitter: Jitter factor (0.0 to 1.0) to add randomness.
            retryable_status_codes: HTTP status codes that trigger retry.
        """
        if max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if base_delay <= 0:
            raise ValueError("Base delay must be positive")
        if max_delay <= 0:
            raise ValueError("Max delay must be positive")
        if not 0.0 <= jitter <= 1.0:
            raise ValueError("Jitter must be between 0.0 and 1.0")

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_status_codes = retryable_status_codes or {
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        }

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (1-indexed).

        Returns:
            Delay in seconds.
        """
        # Exponential backoff: base_delay * 2^(attempt-1)
        delay = self.base_delay * (2 ** (attempt - 1))

        # Cap at max_delay
        capped = min(float(delay), self.max_delay)

        # Add jitter: random factor between (1-jitter) and (1+jitter)
        if self.jitter > 0:
            jitter_factor = 1.0 + random.uniform(-self.jitter, self.jitter)
            return capped * jitter_factor

        return capped

    def _get_retry_after(self, response: httpx.Response | None) -> float | None:
        """Extract Retry-After header value from response.

        Args:
            response: HTTP response with optional Retry-After header.

        Returns:
            Delay in seconds, or None if not present.
        """
        if response is None:
            return None

        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return None

        # Try parsing as seconds
        try:
            return float(retry_after)
        except ValueError:
            pass

        # Try parsing as HTTP-date (simplified)
        # In production, would parse RFC 7231 HTTP-date format
        return None

    async def attempts(self) -> AsyncIterator[int]:
        """Async generator yielding attempt numbers.

        Yields:
            Attempt number (0 to max_retries).
        """
        for attempt in range(self.max_retries + 1):
            yield attempt

    async def apply_backoff(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Apply backoff delay after a failed attempt.

        Respects Retry-After header if present, otherwise uses exponential backoff.

        Args:
            attempt: Current attempt number.
            response: HTTP response (optional, for Retry-After header).

        Returns:
            Actual delay applied in seconds.
        """
        # Check for Retry-After header first
        retry_after = self._get_retry_after(response)
        delay: float = retry_after if retry_after is not None else self._calculate_backoff(attempt)

        await asyncio.sleep(delay)
        return delay

    def is_retryable(self, status_code: int) -> bool:
        """Check if a status code should trigger a retry.

        Args:
            status_code: HTTP status code.

        Returns:
            True if the status code is retryable.
        """
        return status_code in self.retryable_status_codes