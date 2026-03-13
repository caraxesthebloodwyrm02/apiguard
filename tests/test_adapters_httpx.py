"""Tests for AsyncRateLimitedClient."""

from unittest.mock import AsyncMock, patch

import pytest

from apiguard.adapters.httpx import AsyncRateLimitedClient
from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker
from apiguard.exceptions import CircuitOpenError


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