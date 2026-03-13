"""Circuit breaker implementation."""

import threading
import time
from enum import Enum
from typing import Self

from apiguard.exceptions import CircuitOpenError


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Thread-safe circuit breaker with CLOSED/OPEN/HALF_OPEN states.

    The circuit breaker protects against cascading failures by tracking
    failures and opening the circuit when the threshold is exceeded.

    States:
        - CLOSED: Normal operation, requests pass through.
        - OPEN: Failures exceeded threshold, requests fail fast.
        - HALF_OPEN: Recovery timeout elapsed, testing if service recovered.

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        try:
            with breaker:
                result = make_api_call()
        except CircuitOpenError:
            # Handle open circuit
            pass
    """

    def __init__(
        self,
        failure_threshold: int,
        recovery_timeout: float,
        success_threshold: int = 1,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures to open circuit.
            recovery_timeout: Seconds to wait before transitioning to HALF_OPEN.
            success_threshold: Successful calls in HALF_OPEN to close circuit.
        """
        if failure_threshold <= 0:
            raise ValueError("Failure threshold must be positive")
        if recovery_timeout <= 0:
            raise ValueError("Recovery timeout must be positive")
        if success_threshold <= 0:
            raise ValueError("Success threshold must be positive")

        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._update_state()
            return self._state

    def _update_state(self) -> None:
        """Update circuit state based on timing."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time is not None
            and time.monotonic() - self._last_failure_time >= self._recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0

    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._last_failure_time = None
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Failure in HALF_OPEN goes back to OPEN
                self._state = CircuitState.OPEN
                self._last_failure_time = time.monotonic()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN

    def __enter__(self) -> Self:
        """Enter context manager.

        Raises:
            CircuitOpenError: If circuit is OPEN.
        """
        with self._lock:
            self._update_state()
            if self._state == CircuitState.OPEN:
                raise CircuitOpenError(
                    "Circuit breaker is OPEN",
                    recovery_timeout=self._recovery_timeout,
                )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, recording success or failure."""
        if exc_type is not None:
            self._record_failure()
        else:
            self._record_success()

    def is_closed(self) -> bool:
        """Check if circuit is closed (allowing requests)."""
        return self.state == CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self.state == CircuitState.OPEN

    def is_half_open(self) -> bool:
        """Check if circuit is in half-open state (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN

    def reset(self) -> None:
        """Reset circuit to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None