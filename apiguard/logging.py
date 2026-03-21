"""Structured log event helpers for APIGuard."""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(Enum):
    """Log event types."""

    RATE_LIMIT_ACQUIRED = "rate_limit.acquired"
    RATE_LIMIT_EXHAUSTED = "rate_limit.exhausted"
    RETRY_ATTEMPT = "retry.attempt"
    RETRY_EXHAUSTED = "retry.exhausted"
    CIRCUIT_STATE_CHANGE = "circuit.state_change"
    CIRCUIT_FAILURE = "circuit.failure"


@dataclass
class LogEvent:
    """Structured log event.

    Attributes:
        event_type: Type of the event.
        timestamp: Unix timestamp (seconds).
        data: Event-specific data.
    """

    event_type: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert event to JSON string.

        Returns:
            JSON representation of the event.
        """
        return json.dumps(
            {
                "event_type": self.event_type,
                "timestamp": self.timestamp,
                **self.data,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of the event.
        """
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            **self.data,
        }


def log_event(event: LogEvent, logger: logging.Logger | None = None) -> None:
    """Log a structured event.

    Args:
        event: The event to log.
        logger: Logger to use (defaults to 'apiguard' logger).
    """
    if logger is None:
        logger = logging.getLogger("apiguard")
    logger.info(event.to_json())


def create_rate_limit_event(
    acquired: bool,
    tokens: int,
    available: float,
    key: str | None = None,
) -> LogEvent:
    """Create a rate limit log event.

    Args:
        acquired: Whether tokens were acquired.
        tokens: Number of tokens requested.
        available: Available tokens before request.
        key: Optional bucket key (for registry).

    Returns:
        Log event for the rate limit action.
    """
    event_type = (
        EventType.RATE_LIMIT_ACQUIRED.value if acquired else EventType.RATE_LIMIT_EXHAUSTED.value
    )
    data: dict[str, Any] = {
        "tokens_requested": tokens,
        "tokens_available": available,
    }
    if key is not None:
        data["bucket_key"] = key
    return LogEvent(event_type=event_type, data=data)


def create_retry_event(
    attempt: int,
    max_retries: int,
    delay: float | None = None,
    error: str | None = None,
) -> LogEvent:
    """Create a retry log event.

    Args:
        attempt: Current attempt number.
        max_retries: Maximum retries.
        delay: Delay before next retry (optional).
        error: Error message (optional).

    Returns:
        Log event for the retry action.
    """
    data: dict[str, Any] = {
        "attempt": attempt,
        "max_retries": max_retries,
    }
    if delay is not None:
        data["delay"] = delay
    if error is not None:
        data["error"] = error

    event_type = (
        EventType.RETRY_ATTEMPT.value if attempt < max_retries else EventType.RETRY_EXHAUSTED.value
    )
    return LogEvent(event_type=event_type, data=data)


def create_circuit_event(
    from_state: str,
    to_state: str,
    failure_count: int | None = None,
    success_count: int | None = None,
) -> LogEvent:
    """Create a circuit breaker state change event.

    Args:
        from_state: Previous state.
        to_state: New state.
        failure_count: Current failure count (optional).
        success_count: Current success count (optional).

    Returns:
        Log event for the state change.
    """
    data: dict[str, Any] = {
        "from_state": from_state,
        "to_state": to_state,
    }
    if failure_count is not None:
        data["failure_count"] = failure_count
    if success_count is not None:
        data["success_count"] = success_count
    return LogEvent(event_type=EventType.CIRCUIT_STATE_CHANGE.value, data=data)


def create_circuit_failure_event(
    state: str,
    failure_count: int,
    threshold: int,
) -> LogEvent:
    """Create a circuit breaker failure event.

    Args:
        state: Current state.
        failure_count: Current failure count.
        threshold: Failure threshold.

    Returns:
        Log event for the failure.
    """
    return LogEvent(
        event_type=EventType.CIRCUIT_FAILURE.value,
        data={
            "state": state,
            "failure_count": failure_count,
            "threshold": threshold,
        },
    )
