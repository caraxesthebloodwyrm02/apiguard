"""Smoke benchmark for APIGuard core operations.

This is a minimal measurement shard to establish baseline latency
for token acquisition (the core synchronous operation).
Run with: uv run pytest tests/bench_smoke.py -v
"""

import time
import json
from pathlib import Path

import pytest

from apiguard.bucket import TokenBucket


class TestSmokeBenchmark:
    """Smoke benchmark tests for APIGuard core operations."""

    def test_token_acquisition_latency(self, tmp_path: Path) -> None:
        """Measure token acquisition latency under normal load."""
        bucket = TokenBucket(capacity=1000, refill_rate=100.0)

        # Warm up
        for _ in range(100):
            bucket.acquire(1)

        # Measure 10000 acquisitions
        start = time.perf_counter()
        for _ in range(10000):
            bucket.acquire(1)
        elapsed = time.perf_counter() - start

        # Save metrics
        metrics = {
            "test": "token_acquisition_latency",
            "iterations": 10000,
            "total_seconds": elapsed,
            "avg_ms_per_op": (elapsed / 10000) * 1000,
            "ops_per_second": 10000 / elapsed,
            "timestamp": time.time(),
        }

        output_file = tmp_path / "bench_smoke_token_acquisition.json"
        output_file.write_text(json.dumps(metrics, indent=2))

        # Assert reasonable performance (< 0.1ms per operation)
        assert metrics["avg_ms_per_op"] < 0.1, f"Token acquisition too slow: {metrics}"

        # Also print to console for visibility
        print(f"\nToken bucket performance: {metrics['ops_per_second']:.0f} ops/sec ({metrics['avg_ms_per_op']:.4f} ms/op)")

    def test_token_bucket_capacity_latency(self, tmp_path: Path) -> None:
        """Measure token bucket capacity check latency."""
        bucket = TokenBucket(capacity=1000, refill_rate=100.0)

        # Warm up
        for _ in range(100):
            bucket.available()

        # Measure 10000 capacity checks
        start = time.perf_counter()
        for _ in range(10000):
            bucket.available()
        elapsed = time.perf_counter() - start

        # Save metrics
        metrics = {
            "test": "token_bucket_capacity_latency",
            "iterations": 10000,
            "total_seconds": elapsed,
            "avg_ms_per_op": (elapsed / 10000) * 1000,
            "ops_per_second": 10000 / elapsed,
            "timestamp": time.time(),
        }

        output_file = tmp_path / "bench_smoke_capacity_check.json"
        output_file.write_text(json.dumps(metrics, indent=2))

        # Assert reasonable performance (< 0.05ms per operation)
        assert metrics["avg_ms_per_op"] < 0.05, f"Capacity check too slow: {metrics}"

        print(f"\nCapacity check performance: {metrics['ops_per_second']:.0f} ops/sec ({metrics['avg_ms_per_op']:.4f} ms/op)")
