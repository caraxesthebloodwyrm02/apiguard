"""Tests for AsyncRateLimitedClient."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from apiguard.adapters.httpx import AsyncRateLimitedClient
from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker
from apiguard.exceptions import CircuitOpenError, RetryExhaustedError
from apiguard.retry import RetryHandler


class TestAsyncRateLimitedClient:
    """Test suite for AsyncRateLimitedClient."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Context manager initializes and closes client."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                assert client._client is not None
            # Client is closed and set to None after context exit
            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_tokens(self) -> None:
        """Client acquires tokens for requests."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                assert client._bucket.available() == pytest.approx(100.0, rel=1e-3)
                await client._acquire_tokens(10)
                assert client._bucket.available() == pytest.approx(90.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_acquire_tokens_insufficient(self) -> None:
        """Acquiring more tokens than available raises error."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                with pytest.raises(RuntimeError, match="Failed to acquire"):
                    await client._acquire_tokens(20)

    @pytest.mark.asyncio
    async def test_check_circuit_open(self) -> None:
        """check_circuit raises CircuitOpenError if open."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        client = AsyncRateLimitedClient(bucket=bucket, breaker=breaker)

        # Open circuit
        try:
            with breaker:
                raise ValueError("error")
        except ValueError:
            pass

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                with pytest.raises(CircuitOpenError):
                    client._check_circuit()

    @pytest.mark.asyncio
    async def test_check_circuit_no_breaker(self) -> None:
        """check_circuit does nothing if no breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                # Should not raise
                client._check_circuit()

    def test_check_client_not_initialized(self) -> None:
        """_check_client raises if not initialized."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        with pytest.raises(RuntimeError, match="not initialized"):
            client._check_client()

    @pytest.mark.asyncio
    async def test_check_client_returns_client(self) -> None:
        """_check_client returns the httpx client when initialized."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_client):
            async with client:
                result = client._check_client()
                assert result is mock_client

    @pytest.mark.asyncio
    async def test_request_no_breaker(self) -> None:
        """request() works without circuit breaker."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=200)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.request("GET", "/test")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_breaker(self) -> None:
        """request() delegates to circuit breaker when present."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        client = AsyncRateLimitedClient(bucket=bucket, breaker=breaker)

        mock_response = httpx.Response(status_code=200)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.request("GET", "/test")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_reraises_exception(self) -> None:
        """request() re-raises non-CircuitOpenError exceptions."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                with pytest.raises(httpx.ConnectError):
                    await client.request("GET", "/test")

    @pytest.mark.asyncio
    async def test_request_with_retry_retryable_status(self) -> None:
        """Retry logic retries on retryable status codes."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        retry = RetryHandler(max_retries=2, base_delay=0.01, jitter=0.0)
        client = AsyncRateLimitedClient(bucket=bucket, retry=retry)

        responses = [
            httpx.Response(status_code=429, headers={"Retry-After": "0"}),
            httpx.Response(status_code=200),
        ]
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=responses)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.request("GET", "/test")
                assert resp.status_code == 200
                assert mock_http.request.call_count == 2

    @pytest.mark.asyncio
    async def test_request_with_retry_http_error(self) -> None:
        """Retry logic retries on HTTPError then succeeds."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        retry = RetryHandler(max_retries=2, base_delay=0.01, jitter=0.0)
        client = AsyncRateLimitedClient(bucket=bucket, retry=retry)

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=[httpx.ConnectError("fail"), httpx.Response(status_code=200)])
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.request("GET", "/test")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_retry_exhausted(self) -> None:
        """RetryExhaustedError raised when all retries fail."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        retry = RetryHandler(max_retries=1, base_delay=0.01, jitter=0.0)
        client = AsyncRateLimitedClient(bucket=bucket, retry=retry)

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("fail"))
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                with pytest.raises(RetryExhaustedError):
                    await client.request("GET", "/test")

    @pytest.mark.asyncio
    async def test_retry_exhausted_on_status_codes(self) -> None:
        """RetryExhaustedError raised when retryable status persists."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        retry = RetryHandler(max_retries=1, base_delay=0.01, jitter=0.0)
        client = AsyncRateLimitedClient(bucket=bucket, retry=retry)

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=httpx.Response(status_code=503))
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                with pytest.raises(RetryExhaustedError):
                    await client.request("GET", "/test")

    @pytest.mark.asyncio
    async def test_get_shortcut(self) -> None:
        """get() calls request with GET method."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=200)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.get("/test")
                assert resp.status_code == 200
                mock_http.request.assert_called_once_with("GET", "/test")

    @pytest.mark.asyncio
    async def test_post_shortcut(self) -> None:
        """post() calls request with POST method."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=201)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.post("/test", json={"key": "val"})
                assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_put_shortcut(self) -> None:
        """put() calls request with PUT method."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=200)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.put("/test")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_shortcut(self) -> None:
        """patch() calls request with PATCH method."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=200)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.patch("/test")
                assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_shortcut(self) -> None:
        """delete() calls request with DELETE method."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        client = AsyncRateLimitedClient(bucket=bucket)

        mock_response = httpx.Response(status_code=204)
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_http.aclose = AsyncMock()

        with patch("apiguard.adapters.httpx.httpx.AsyncClient", return_value=mock_http):
            async with client:
                resp = await client.delete("/test")
                assert resp.status_code == 204
