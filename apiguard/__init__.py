"""APIGuard - Production-grade rate limiting, retry, and circuit breaking library."""

from apiguard.bucket import TokenBucket
from apiguard.circuit import CircuitBreaker, CircuitState
from apiguard.client import RateLimitedClient
from apiguard.exceptions import CircuitOpenError, RetryExhaustedError
from apiguard.registry import BucketRegistry
from apiguard.retry import RetryHandler

__all__ = [
    "TokenBucket",
    "RetryHandler",
    "CircuitBreaker",
    "CircuitState",
    "RateLimitedClient",
    "BucketRegistry",
    "CircuitOpenError",
    "RetryExhaustedError",
]

__version__ = "0.1.0"