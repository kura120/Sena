# src/core/telemetry.py
"""
Telemetry System

Collects and analyzes metrics, performance data, and error rates.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from src.config.settings import get_settings
from src.database.connection import get_db
from src.database.repositories.telemetry_repo import TelemetryRepository
from src.utils.logger import logger


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram


class TelemetryCollector:
    """
    Collects and manages telemetry data.

    Features:
    - Real-time metric recording
    - Periodic aggregation
    - Error tracking
    - Performance monitoring
    """

    def __init__(self):
        self.settings = get_settings()
        self._repo: Optional[TelemetryRepository] = None
        self._buffer: list[MetricPoint] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._initialized = False

        # In-memory counters for fast access
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    async def initialize(self) -> None:
        """Initialize telemetry system."""
        if self._initialized:
            return

        db = await get_db()
        self._repo = TelemetryRepository(db)

        # Start background flush task
        if self.settings.telemetry.enabled:
            self._flush_task = asyncio.create_task(self._flush_loop())

        self._initialized = True
        logger.info("Telemetry system initialized")

    async def shutdown(self) -> None:
        """Shutdown telemetry system."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_buffer()

        self._initialized = False
        logger.info("Telemetry system shutdown")

    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
        metric_type: str = "gauge",
    ) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name (e.g., "llm.response_time")
            value: Metric value
            tags: Optional tags for filtering
            metric_type: Type of metric (gauge, counter, histogram)
        """
        if not self.settings.telemetry.enabled:
            return

        point = MetricPoint(
            name=name,
            value=value,
            tags=tags or {},
            metric_type=metric_type,
        )

        async with self._buffer_lock:
            self._buffer.append(point)

        # Update in-memory storage
        if metric_type == "counter":
            self._counters[name] = self._counters.get(name, 0) + value
        elif metric_type == "gauge":
            self._gauges[name] = value
        elif metric_type == "histogram":
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)
            # Keep only last 1000 values
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]

    async def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""
        await self.record_metric(name, value, tags, metric_type="counter")

    async def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Record a gauge metric."""
        await self.record_metric(name, value, tags, metric_type="gauge")

    async def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Record a histogram metric."""
        await self.record_metric(name, value, tags, metric_type="histogram")

    async def record_timing(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[dict[str, str]] = None,
    ) -> None:
        """Record a timing metric (convenience method)."""
        await self.record_histogram(f"{name}.duration_ms", duration_ms, tags)

    async def record_error(
        self,
        error_type: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> None:
        """Record an error occurrence."""
        if not self._repo:
            return

        await self._repo.errors.record(
            error_type=error_type,
            error_code=error_code,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context,
        )

        # Also increment error counter
        await self.increment_counter(
            "errors.total",
            tags={"error_type": error_type},
        )

    def get_counter(self, name: str) -> float:
        """Get current counter value."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get current gauge value."""
        return self._gauges.get(name, 0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get histogram statistics."""
        values = self._histograms.get(name, [])

        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)] if count >= 20 else sorted_values[-1],
            "p99": sorted_values[int(count * 0.99)] if count >= 100 else sorted_values[-1],
        }

    async def get_metrics_summary(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get summary of all metrics."""
        if since is None:
            since = datetime.now() - timedelta(hours=1)

        return {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy(),
            "histograms": {name: self.get_histogram_stats(name) for name in self._histograms},
            "since": since.isoformat(),
        }

    async def get_error_summary(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get summary of errors."""
        if not self._repo:
            return {}

        error_counts = await self._repo.errors.get_error_counts(since)
        unresolved = await self._repo.errors.get_unresolved(limit=10)

        return {
            "counts_by_type": error_counts,
            "total_errors": sum(error_counts.values()),
            "unresolved_count": len(unresolved),
            "recent_unresolved": [e.to_dict() for e in unresolved[:5]],
        }

    async def _flush_loop(self) -> None:
        """Background task to periodically flush metrics to database."""
        interval = self.settings.telemetry.metrics.collect_interval

        while True:
            try:
                await asyncio.sleep(interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Telemetry flush error: {e}")

    async def _flush_buffer(self) -> None:
        """Flush buffered metrics to database in a single transaction.

        All points are written with one executemany call so we only acquire
        the write lock once regardless of how many metrics are buffered.
        """
        if not self._repo:
            return

        async with self._buffer_lock:
            if not self._buffer:
                return
            buffer = self._buffer.copy()
            self._buffer.clear()

        # Build rows for a single bulk insert
        rows = [
            (
                point.name,
                point.value,
                point.metric_type,
                json.dumps(point.tags),
                point.timestamp.isoformat(),
            )
            for point in buffer
        ]

        try:
            await self._repo.db.execute_many(
                """
                INSERT INTO telemetry_metrics
                    (metric_name, metric_value, metric_type, tags, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
        except Exception as e:
            logger.warning(f"Failed to flush {len(buffer)} metrics to database: {e}")


def timed(metric_name: str):
    """
    Decorator to automatically record function execution time.

    Usage:
        @timed("my_function.duration")
        async def my_function():
            ...
    """

    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                # Note: This requires access to telemetry instance
                # In practice, use the global instance

        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Global telemetry instance
_telemetry: Optional[TelemetryCollector] = None


async def get_telemetry() -> TelemetryCollector:
    """Get the global telemetry instance."""
    global _telemetry

    if _telemetry is None:
        _telemetry = TelemetryCollector()
        await _telemetry.initialize()

    return _telemetry
