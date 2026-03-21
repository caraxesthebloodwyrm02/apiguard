"""Tests for TokenBucket."""

import threading
import time

import pytest

from apiguard.bucket import TokenBucket


class TestTokenBucket:
    """Test suite for TokenBucket."""

    def test_initial_state(self) -> None:
        """Bucket starts at full capacity."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.available() == 100.0

    def test_acquire_tokens(self) -> None:
        """Tokens can be acquired from bucket."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.acquire(tokens=10) is True
        assert bucket.available() == pytest.approx(90.0, rel=1e-3)

    def test_acquire_more_than_available(self) -> None:
        """Acquiring more than available returns False."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        assert bucket.acquire(tokens=20) is False
        assert bucket.available() == 10.0  # No tokens consumed

    def test_acquire_zero_tokens_raises(self) -> None:
        """Acquiring zero or negative tokens raises error."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        with pytest.raises(ValueError, match="must be positive"):
            bucket.acquire(tokens=0)
        with pytest.raises(ValueError, match="must be positive"):
            bucket.acquire(tokens=-1)

    def test_refill(self) -> None:
        """Bucket refills over time."""
        bucket = TokenBucket(capacity=100, refill_rate=100.0)  # 100 tokens/sec
        bucket.acquire(tokens=100)
        assert bucket.available() == pytest.approx(0.0, abs=0.01)

        time.sleep(0.1)  # Should refill ~10 tokens
        available = bucket.available()
        assert 9.0 < available < 11.0

    def test_refill_cap(self) -> None:
        """Bucket doesn't exceed capacity."""
        bucket = TokenBucket(capacity=100, refill_rate=100.0)
        time.sleep(0.1)  # Would refill 10 tokens, but already at capacity
        assert bucket.available() == 100.0

    def test_context_manager(self) -> None:
        """Context manager acquires tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        with bucket(tokens=5):
            assert bucket.available() == pytest.approx(95.0, rel=1e-3)

    def test_context_manager_failure(self) -> None:
        """Context manager raises on insufficient tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        with pytest.raises(RuntimeError, match="Failed to acquire"), bucket(tokens=20):
            pass

    def test_invalid_capacity(self) -> None:
        """Zero or negative capacity raises error."""
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucket(capacity=0, refill_rate=10.0)
        with pytest.raises(ValueError, match="Capacity must be positive"):
            TokenBucket(capacity=-1, refill_rate=10.0)

    def test_invalid_refill_rate(self) -> None:
        """Zero or negative refill rate raises error."""
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucket(capacity=100, refill_rate=0.0)
        with pytest.raises(ValueError, match="Refill rate must be positive"):
            TokenBucket(capacity=100, refill_rate=-1.0)

    def test_thread_safety(self) -> None:
        """Bucket is thread-safe for concurrent access."""
        bucket = TokenBucket(capacity=1000, refill_rate=1000.0)
        success_count = [0]
        lock = threading.Lock()

        def acquire_tokens() -> None:
            for _ in range(100):
                if bucket.acquire(tokens=1):
                    with lock:
                        success_count[0] += 1

        threads = [threading.Thread(target=acquire_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total tokens acquired should not exceed initial capacity
        assert success_count[0] <= 1000

    def test_fractional_tokens(self) -> None:
        """Fractional token counts work correctly."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        assert bucket.acquire(tokens=5) is True
        assert bucket.available() == pytest.approx(5.0, rel=1e-3)

    def test_enter_exit_noop(self) -> None:
        """__enter__ returns self, __exit__ is a no-op."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        with bucket as b:
            assert b is bucket
