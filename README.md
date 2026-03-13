# APIGuard

Production-grade rate limiting, retry, and circuit breaking library for Python.

## Features

- **Token Bucket Rate Limiting**: Thread-safe rate limiting with configurable tokens and refill rate
- **Retry with Backoff**: Exponential backoff with jitter and Retry-After header support
- **Circuit Breaker**: Protects against cascading failures with CLOSED/OPEN/HALF_OPEN states
- **Async Support**: First-class async/await support via httpx adapter
- **Registry**: Per-user/per-resource rate limit tracking
- **Structured Logging**: JSON-structured log events for observability

## Installation

```bash
pip install apiguard
```

## Quick Start

### Basic Rate Limiting

```python
from apiguard import TokenBucket

bucket = TokenBucket(capacity=100, refill_rate=10.0)

if bucket.acquire(tokens=5):
    # Make API call
    pass
else:
    # Wait or reject request
    pass
```

### Circuit Breaker

```python
from apiguard import CircuitBreaker, CircuitOpenError

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
)

try:
    with breaker:
        result = make_api_call()
except CircuitOpenError:
    # Circuit is open, fail fast
    handle_failure()
```

### Retry Handler

```python
from apiguard import RetryHandler, RetryExhaustedError
import httpx

retry = RetryHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    retryable_status_codes={429, 500, 502, 503, 504},
)

async def fetch_with_retry(url: str) -> httpx.Response:
    async for attempt in retry.attempts():
        response = await httpx.get(url)
        if response.status_code in retry.retryable_status_codes:
            retry.apply_backoff(attempt, response)
            continue
        return response
    raise RetryExhaustedError("All retries exhausted")
```

### RateLimitedClient (Composition)

```python
from apiguard import RateLimitedClient, TokenBucket, RetryHandler, CircuitBreaker

client = RateLimitedClient(
    bucket=TokenBucket(capacity=100, refill_rate=10.0),
    retry=RetryHandler(max_retries=3),
    breaker=CircuitBreaker(failure_threshold=5),
)

# Use as context manager
with client:
    response = client.request("GET", "https://api.example.com/data")
```

### Per-User Rate Limiting with Registry

```python
from apiguard import BucketRegistry

registry = BucketRegistry(default_capacity=100, default_refill_rate=10.0)

# Get or create bucket for specific user
user_bucket = registry.get_bucket("user-123")
```

### Async HTTP Client

```python
from apiguard.adapters.httpx import AsyncRateLimitedClient

async with AsyncRateLimitedClient(
    bucket=TokenBucket(capacity=100, refill_rate=10.0),
) as client:
    response = await client.get("https://api.example.com/data")
```

## API Reference

### TokenBucket

- `TokenBucket(capacity: int, refill_rate: float)` - Create a bucket with capacity tokens, refilling at `refill_rate` tokens/second
- `acquire(tokens: int = 1) -> bool` - Try to acquire tokens, returns True if successful
- `available() -> float` - Current token count
- `__enter__` / `__exit__` - Context manager support (no-op, for composition)

### CircuitBreaker

- `CircuitBreaker(failure_threshold: int, recovery_timeout: float, success_threshold: int = 1)` - Configure breaker
- States: `CLOSED`, `OPEN`, `HALF_OPEN`
- `__enter__` - Raises `CircuitOpenError` if circuit is OPEN
- `__exit__(exc_type, exc_val, exc_tb)` - Records success/failure and updates state

### RetryHandler

- `RetryHandler(max_retries: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: float = 0.1, retryable_status_codes: set[int] | None = None)`
- `attempts() -> AsyncIterator[int]` - Async generator yielding attempt numbers
- `apply_backoff(attempt: int, response: httpx.Response | None = None) -> float` - Apply backoff with optional Retry-After header

### RateLimitedClient

- `RateLimitedClient(bucket: TokenBucket, retry: RetryHandler | None = None, breaker: CircuitBreaker | None = None)`
- Composes rate limiting, retry, and circuit breaking
- Thread-safe and reusable

### BucketRegistry

- `BucketRegistry(default_capacity: int, default_refill_rate: float)`
- `get_bucket(key: str) -> TokenBucket` - Get or create bucket for key
- `remove_bucket(key: str) -> bool` - Remove bucket for key

### Exceptions

- `CircuitOpenError` - Raised when circuit is OPEN
- `RetryExhaustedError` - Raised when all retries are exhausted

## Development

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Testing

```bash
pytest                       # run all 60 tests
pytest --cov=apiguard        # with coverage
pytest tests/test_bucket.py  # single module
```

### Linting & Type Checking

```bash
ruff check .                 # lint
ruff format .                # format
mypy apiguard                # strict type checking
```

### Project Layout

```
apiguard/
  bucket.py       Token bucket rate limiter (thread-safe)
  circuit.py      Circuit breaker (CLOSED → OPEN → HALF_OPEN)
  client.py       Composed client (bucket + retry + breaker)
  retry.py        Exponential backoff with jitter & Retry-After
  registry.py     Per-key bucket registry
  exceptions.py   CircuitOpenError, RetryExhaustedError
  logging.py      Structured JSON log events
  adapters/
    httpx.py      Async httpx integration
tests/            Mirrors apiguard/ — one test file per module
```

Requires Python ≥ 3.11. Build system: Hatchling.

## License

MIT