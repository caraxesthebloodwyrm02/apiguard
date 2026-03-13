"""Custom exceptions for APIGuard."""


class CircuitOpenError(Exception):
    """Raised when attempting to use a circuit that is OPEN."""

    def __init__(
        self,
        message: str = "Circuit breaker is OPEN",
        *,
        recovery_timeout: float | None = None,
    ) -> None:
        super().__init__(message)
        self.recovery_timeout = recovery_timeout


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str = "All retry attempts exhausted",
        *,
        attempts: int | None = None,
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error