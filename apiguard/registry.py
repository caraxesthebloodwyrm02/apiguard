"""Bucket registry for per-user rate limiting."""

import threading

from apiguard.bucket import TokenBucket


class BucketRegistry:
    """Registry for managing per-user/per-resource token buckets.

    Maintains a collection of token buckets keyed by identifier,
    useful for per-user rate limiting.

    Example:
        registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)
        user_bucket = registry.get_bucket("user-123")
        if user_bucket.acquire(tokens=5):
            # Process request
            pass
    """

    def __init__(
        self,
        default_capacity: int,
        default_refill_rate: float,
    ) -> None:
        """Initialize the bucket registry.

        Args:
            default_capacity: Default bucket capacity for new buckets.
            default_refill_rate: Default refill rate for new buckets.
        """
        if default_capacity <= 0:
            raise ValueError("Default capacity must be positive")
        if default_refill_rate <= 0:
            raise ValueError("Default refill rate must be positive")

        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def get_bucket(self, key: str) -> TokenBucket:
        """Get or create a bucket for the given key.

        Args:
            key: Unique identifier for the bucket (e.g., user ID).

        Returns:
            Token bucket for the key.
        """
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self._default_capacity,
                    refill_rate=self._default_refill_rate,
                )
            return self._buckets[key]

    def remove_bucket(self, key: str) -> bool:
        """Remove a bucket from the registry.

        Args:
            key: Key of the bucket to remove.

        Returns:
            True if bucket was removed, False if it didn't exist.
        """
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]
                return True
            return False

    def has_bucket(self, key: str) -> bool:
        """Check if a bucket exists for the given key.

        Args:
            key: Key to check.

        Returns:
            True if bucket exists, False otherwise.
        """
        with self._lock:
            return key in self._buckets

    def clear(self) -> None:
        """Remove all buckets from the registry."""
        with self._lock:
            self._buckets.clear()

    def count(self) -> int:
        """Get the number of buckets in the registry.

        Returns:
            Number of buckets.
        """
        with self._lock:
            return len(self._buckets)

    def keys(self) -> list[str]:
        """Get all bucket keys.

        Returns:
            List of all keys in the registry.
        """
        with self._lock:
            return list(self._buckets.keys())