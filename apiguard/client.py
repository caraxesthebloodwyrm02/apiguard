"""Rate-limited client composing bucket, retry, and circuit breaker."""

from typing import Self

from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker
from apiguard.exceptions import CircuitOpenError
from apiguard.retry import RetryHandler


class RateLimitedClient:
    """Rate-limited client composing TokenBucket, RetryHandler, and CircuitBreaker.

    This client coordinates rate limiting, retries, and circuit breaking
    in a single composable interface.

    Example:
        client = RateLimitedClient(
            bucket=TokenBucket(capacity=100, refill_rate=10.0),
            retry=RetryHandler(max_retries=3),
            breaker=CircuitBreaker(failure_threshold=5),
        )

        with client:
            response = client.request("GET", "https://api.example.com/data")
    """

    def __init__(
        self,
        bucket: TokenBucket,
        retry: RetryHandler | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize the rate-limited client.

        Args:
            bucket: Token bucket for rate limiting.
            retry: Retry handler (optional).
            breaker: Circuit breaker (optional).
        """
        self._bucket = bucket
        self._retry = retry
        self._breaker = breaker

    @property
    def bucket(self) -> TokenBucket:
        """Get the token bucket."""
        return self._bucket

    @property
    def retry(self) -> RetryHandler | None:
        """Get the retry handler."""
        return self._retry

    @property
    def breaker(self) -> CircuitBreaker | None:
        """Get the circuit breaker."""
        return self._breaker

    def __enter__(self) -> Self:
        """Enter context manager (delegates to circuit breaker if present)."""
        if self._breaker is not None:
            self._breaker.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager."""
        if self._breaker is not None:
            self._breaker.__exit__(exc_type, exc_val, exc_tb)

    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens acquired, False otherwise.
        """
        return self._bucket.acquire(tokens)

    def available(self) -> float:
        """Get available tokens."""
        return self._bucket.available()

    def check_circuit(self) -> None:
        """Check if circuit is closed.

        Raises:
            CircuitOpenError: If circuit is open.
        """
        if self._breaker is not None and self._breaker.is_open():
            raise CircuitOpenError(
                "Circuit breaker is OPEN",
                recovery_timeout=self._breaker._recovery_timeout,
            )
