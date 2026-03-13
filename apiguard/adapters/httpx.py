"""Async HTTP client adapter using httpx."""

from typing import Any, Self

import httpx

from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker
from apiguard.exceptions import CircuitOpenError, RetryExhaustedError
from apiguard.retry import RetryHandler


class AsyncRateLimitedClient:
    """Async HTTP client with rate limiting, retry, and circuit breaking.

    Wraps httpx.AsyncClient with TokenBucket rate limiting, RetryHandler
    retry logic, and CircuitBreaker protection.

    Example:
        async with AsyncRateLimitedClient(
            bucket=TokenBucket(capacity=100, refill_rate=10.0),
        ) as client:
            response = await client.get("https://api.example.com/data")
    """

    def __init__(
        self,
        bucket: TokenBucket,
        retry: RetryHandler | None = None,
        breaker: CircuitBreaker | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the async rate-limited client.

        Args:
            bucket: Token bucket for rate limiting.
            retry: Retry handler (optional).
            breaker: Circuit breaker (optional).
            base_url: Base URL for requests (optional).
            timeout: Request timeout in seconds.
            headers: Default headers (optional).
        """
        self._bucket = bucket
        self._retry = retry
        self._breaker = breaker
        self._base_url = base_url
        self._timeout = timeout
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        base_url = self._base_url if self._base_url is not None else ""
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=self._timeout,
            headers=self._headers,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _check_client(self) -> httpx.AsyncClient:
        """Ensure client is initialized.

        Returns:
            The httpx client.

        Raises:
            RuntimeError: If client is not initialized.
        """
        if self._client is None:
            raise RuntimeError("Client not initialized - use async context manager")
        return self._client

    def _check_circuit(self) -> None:
        """Check if circuit is closed.

        Raises:
            CircuitOpenError: If circuit is open.
        """
        if self._breaker is not None and self._breaker.is_open():
            raise CircuitOpenError(
                "Circuit breaker is OPEN",
                recovery_timeout=self._breaker._recovery_timeout,
            )

    async def _acquire_tokens(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Raises:
            RuntimeError: If tokens cannot be acquired.
        """
        if not self._bucket.acquire(tokens):
            raise RuntimeError(f"Failed to acquire {tokens} tokens")

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a request with retry logic.

        Args:
            method: HTTP method.
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.

        Raises:
            RetryExhaustedError: If all retries are exhausted.
        """
        client = self._check_client()

        if self._retry is None:
            return await client.request(method, url, **kwargs)

        last_error: Exception | None = None
        attempt = 0

        async for attempt in self._retry.attempts():
            try:
                response = await client.request(method, url, **kwargs)

                if response.status_code in self._retry.retryable_status_codes:
                    await self._retry.apply_backoff(attempt, response)
                    continue

                return response

            except httpx.HTTPError as e:
                last_error = e
                if attempt < self._retry.max_retries:
                    await self._retry.apply_backoff(attempt)

        raise RetryExhaustedError(
            "All retry attempts exhausted",
            attempts=attempt,
            last_error=last_error,
        )

    async def request(
        self,
        method: str,
        url: str,
        tokens: int = 1,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a rate-limited request.

        Args:
            method: HTTP method.
            url: Request URL.
            tokens: Tokens to acquire from bucket.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.

        Raises:
            CircuitOpenError: If circuit is open.
            RuntimeError: If tokens cannot be acquired.
            RetryExhaustedError: If all retries exhausted.
        """
        self._check_circuit()
        await self._acquire_tokens(tokens)

        if self._breaker is not None:
            with self._breaker:
                return await self._request_with_retry(method, url, **kwargs)
        return await self._request_with_retry(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request.

        Args:
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.
        """
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request.

        Args:
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.
        """
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a PUT request.

        Args:
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.
        """
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a PATCH request.

        Args:
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.
        """
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request.

        Args:
            url: Request URL.
            **kwargs: Additional request arguments.

        Returns:
            HTTP response.
        """
        return await self.request("DELETE", url, **kwargs)