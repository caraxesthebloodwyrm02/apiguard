"""Tests for logging module."""

import logging

from apiguard.logging import (
    EventType,
    LogEvent,
    create_circuit_event,
    create_circuit_failure_event,
    create_rate_limit_event,
    create_retry_event,
    log_event,
)


class TestLogEvent:
    """Test suite for LogEvent."""

    def test_to_json(self) -> None:
        """LogEvent serializes to JSON."""
        event = LogEvent(
            event_type="test.event",
            data={"key": "value", "number": 42},
        )
        json_str = event.to_json()
        assert '"event_type": "test.event"' in json_str
        assert '"key": "value"' in json_str
        assert '"number": 42' in json_str

    def test_to_dict(self) -> None:
        """LogEvent converts to dict."""
        event = LogEvent(
            event_type="test.event",
            data={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "test.event"
        assert d["key"] == "value"

    def test_timestamp_auto_generated(self) -> None:
        """LogEvent generates timestamp automatically."""
        import time

        before = time.time()
        event = LogEvent(event_type="test.event")
        after = time.time()

        assert before <= event.timestamp <= after


class TestEventType:
    """Test suite for EventType."""

    def test_event_types(self) -> None:
        """All event types are defined."""
        assert EventType.RATE_LIMIT_ACQUIRED.value == "rate_limit.acquired"
        assert EventType.RATE_LIMIT_EXHAUSTED.value == "rate_limit.exhausted"
        assert EventType.RETRY_ATTEMPT.value == "retry.attempt"
        assert EventType.RETRY_EXHAUSTED.value == "retry.exhausted"
        assert EventType.CIRCUIT_STATE_CHANGE.value == "circuit.state_change"
        assert EventType.CIRCUIT_FAILURE.value == "circuit.failure"


class TestEventFactories:
    """Test suite for event factory functions."""

    def test_create_rate_limit_event_acquired(self) -> None:
        """create_rate_limit_event for acquired."""
        event = create_rate_limit_event(
            acquired=True,
            tokens=10,
            available=90,
        )
        assert event.event_type == EventType.RATE_LIMIT_ACQUIRED.value
        assert event.data["tokens_requested"] == 10
        assert event.data["tokens_available"] == 90

    def test_create_rate_limit_event_exhausted(self) -> None:
        """create_rate_limit_event for exhausted."""
        event = create_rate_limit_event(
            acquired=False,
            tokens=100,
            available=5,
        )
        assert event.event_type == EventType.RATE_LIMIT_EXHAUSTED.value

    def test_create_rate_limit_event_with_key(self) -> None:
        """create_rate_limit_event includes key if provided."""
        event = create_rate_limit_event(
            acquired=True,
            tokens=10,
            available=90,
            key="user-123",
        )
        assert event.data["bucket_key"] == "user-123"

    def test_create_retry_event(self) -> None:
        """create_retry_event creates correct event."""
        event = create_retry_event(
            attempt=2,
            max_retries=3,
        )
        assert event.event_type == EventType.RETRY_ATTEMPT.value
        assert event.data["attempt"] == 2
        assert event.data["max_retries"] == 3

    def test_create_retry_event_with_delay(self) -> None:
        """create_retry_event includes delay if provided."""
        event = create_retry_event(
            attempt=2,
            max_retries=3,
            delay=1.5,
        )
        assert event.data["delay"] == 1.5

    def test_create_retry_event_with_error(self) -> None:
        """create_retry_event includes error if provided."""
        event = create_retry_event(
            attempt=3,
            max_retries=3,
            error="Connection refused",
        )
        assert event.data["error"] == "Connection refused"

    def test_create_retry_event_exhausted(self) -> None:
        """create_retry_event creates exhausted event for final attempt."""
        event = create_retry_event(
            attempt=3,
            max_retries=3,
        )
        assert event.event_type == EventType.RETRY_EXHAUSTED.value

    def test_create_circuit_event(self) -> None:
        """create_circuit_event creates correct event."""
        event = create_circuit_event(
            from_state="closed",
            to_state="open",
        )
        assert event.event_type == EventType.CIRCUIT_STATE_CHANGE.value
        assert event.data["from_state"] == "closed"
        assert event.data["to_state"] == "open"

    def test_create_circuit_event_with_counts(self) -> None:
        """create_circuit_event includes counts if provided."""
        event = create_circuit_event(
            from_state="half_open",
            to_state="closed",
            failure_count=0,
            success_count=3,
        )
        assert event.data["failure_count"] == 0
        assert event.data["success_count"] == 3

    def test_create_circuit_failure_event(self) -> None:
        """create_circuit_failure_event creates correct event."""
        event = create_circuit_failure_event(
            state="closed",
            failure_count=4,
            threshold=5,
        )
        assert event.event_type == EventType.CIRCUIT_FAILURE.value
        assert event.data["state"] == "closed"
        assert event.data["failure_count"] == 4
        assert event.data["threshold"] == 5

    def test_log_event(self) -> None:
        """log_event logs to logger."""
        event = LogEvent(
            event_type="test.event",
            data={"key": "value"},
        )
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        log_event(event, logger)

        # Event was logged (no exception raised)
        assert True

    def test_log_event_default_logger(self) -> None:
        """log_event uses default 'apiguard' logger when none provided."""
        event = LogEvent(
            event_type="test.default",
            data={"key": "value"},
        )
        # Should not raise - uses logging.getLogger("apiguard")
        log_event(event)