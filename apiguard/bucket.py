"""Token bucket rate limiting implementation."""

import threading
import time
from collections.abc import Generator
from contextlib import contextmanager


class TokenBucket:
    """Thread-safe token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting. Tokens are added
    at a fixed rate up to a maximum capacity. Each request consumes tokens.

    Example:
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        if bucket.acquire(tokens=5):
            # Make API call
            pass
    """

    def __init__(self, capacity: int, refill_rate: float) -> None:
        """Initialize the token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_rate: Number of tokens added per second.
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("Refill rate must be positive")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens: float = float(capacity)
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(
                self._capacity,
                self._tokens + (elapsed * self._refill_rate),
            )
            self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens were acquired, False if insufficient tokens available.
        """
        if tokens <= 0:
            raise ValueError("Tokens must be positive")

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def available(self) -> float:
        """Get the current number of available tokens.

        Returns:
            Current token count (may be fractional).
        """
        with self._lock:
            self._refill()
            return self._tokens

    @contextmanager
    def __call__(self, tokens: int = 1) -> Generator[None]:
        """Context manager for acquiring tokens.

        Args:
            tokens: Number of tokens to acquire.

        Yields:
            None if tokens acquired successfully.

        Raises:
            RuntimeError: If tokens cannot be acquired.
        """
        acquired = self.acquire(tokens)
        if not acquired:
            raise RuntimeError(f"Failed to acquire {tokens} tokens")
        try:
            yield
        finally:
            # Tokens are consumed, not returned
            pass

    def __enter__(self) -> "TokenBucket":
        """Enter context manager (no-op)."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit context manager (no-op)."""
        pass
