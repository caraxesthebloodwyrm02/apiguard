"""Tests for BucketRegistry."""

import pytest

from apiguard.bucket import TokenBucket
from apiguard.registry import BucketRegistry


class TestBucketRegistry:
    """Test suite for BucketRegistry."""

    def test_get_bucket_creates_new(self) -> None:
        """get_bucket creates bucket for new key."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        bucket = registry.get_bucket("user-123")

        assert isinstance(bucket, TokenBucket)
        assert bucket.available() == 100.0

    def test_get_bucket_returns_existing(self) -> None:
        """get_bucket returns same bucket for same key."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        bucket1 = registry.get_bucket("user-123")
        bucket2 = registry.get_bucket("user-123")

        assert bucket1 is bucket2

    def test_get_bucket_different_keys(self) -> None:
        """Different keys get different buckets."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        bucket1 = registry.get_bucket("user-1")
        bucket2 = registry.get_bucket("user-2")

        assert bucket1 is not bucket2

    def test_remove_bucket(self) -> None:
        """remove_bucket removes bucket from registry."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        registry.get_bucket("user-123")

        assert registry.remove_bucket("user-123") is True
        assert registry.has_bucket("user-123") is False

    def test_remove_nonexistent_bucket(self) -> None:
        """remove_bucket returns False for nonexistent key."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        assert registry.remove_bucket("nonexistent") is False

    def test_has_bucket(self) -> None:
        """has_bucket checks if bucket exists."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)

        assert registry.has_bucket("user-123") is False
        registry.get_bucket("user-123")
        assert registry.has_bucket("user-123") is True

    def test_clear(self) -> None:
        """clear removes all buckets."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        registry.get_bucket("user-1")
        registry.get_bucket("user-2")
        registry.get_bucket("user-3")

        registry.clear()

        assert registry.count() == 0
        assert registry.has_bucket("user-1") is False

    def test_count(self) -> None:
        """count returns number of buckets."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)

        assert registry.count() == 0

        registry.get_bucket("user-1")
        assert registry.count() == 1

        registry.get_bucket("user-2")
        assert registry.count() == 2

        registry.remove_bucket("user-1")
        assert registry.count() == 1

    def test_keys(self) -> None:
        """keys returns all bucket keys."""
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        registry.get_bucket("user-1")
        registry.get_bucket("user-2")

        keys = registry.keys()
        assert set(keys) == {"user-1", "user-2"}

    def test_invalid_capacity(self) -> None:
        """Non-positive default capacity raises error."""
        with pytest.raises(ValueError, match="positive"):
            BucketRegistry(default_capacity=0, default_refill_rate=10.0)
        with pytest.raises(ValueError, match="positive"):
            BucketRegistry(default_capacity=-1, default_refill_rate=10.0)

    def test_invalid_refill_rate(self) -> None:
        """Non-positive default refill rate raises error."""
        with pytest.raises(ValueError, match="positive"):
            BucketRegistry(default_capacity=100, default_refill_rate=0.0)
        with pytest.raises(ValueError, match="positive"):
            BucketRegistry(default_capacity=100, default_refill_rate=-1.0)

    def test_thread_safety(self) -> None:
        """Registry is thread-safe for concurrent access."""
        import threading

        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        keys = [f"user-{i}" for i in range(100)]

        def get_buckets() -> None:
            for key in keys:
                registry.get_bucket(key)

        threads = [threading.Thread(target=get_buckets) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each unique key should have exactly one bucket
        assert registry.count() == 100
