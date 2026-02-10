# src/database/repositories/telemetry_repo.py
"""Telemetry repository."""

from datetime import datetime, timedelta
from typing import Optional

from src.database.connection import DatabaseManager
from src.database.models.telemetry import TelemetryMetric, TelemetryError
from src.database.models.log import Log
from src.database.models.benchmark import Benchmark
from src.database.repositories.base import BaseRepository


class TelemetryRepository:
    """Repository for telemetry operations."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.metrics = MetricsRepository(db)
        self.errors = ErrorsRepository(db)
        self.logs = LogsRepository(db)
        self.benchmarks = BenchmarksRepository(db)


class MetricsRepository(BaseRepository[TelemetryMetric]):
    """Repository for telemetry metrics."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "telemetry_metrics", TelemetryMetric)
    
    async def record(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[dict] = None,
    ) -> int:
        """Record a metric value."""
        metric = TelemetryMetric(
            metric_name=metric_name,
            metric_value=value,
            metric_type=metric_type,
            tags=tags or {},
        )
        return await self.create(metric)
    
    async def get_by_name(
        self,
        metric_name: str,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[TelemetryMetric]:
        """Get metrics by name."""
        if since:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM telemetry_metrics 
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (metric_name, since.isoformat(), limit)
            )
        else:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM telemetry_metrics 
                WHERE metric_name = ?
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (metric_name, limit)
            )
        return [TelemetryMetric.from_row(row) for row in rows]
    
    async def get_aggregated(
        self,
        metric_name: str,
        period: str = "hour",  # hour, day, week
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """Get aggregated metric values."""
        if since is None:
            since = datetime.now() - timedelta(days=7)
        
        # SQLite date grouping
        if period == "hour":
            group_expr = "strftime('%Y-%m-%d %H:00', timestamp)"
        elif period == "day":
            group_expr = "date(timestamp)"
        else:
            group_expr = "strftime('%Y-W%W', timestamp)"
        
        rows = await self.db.fetch_all(
            f"""
            SELECT 
                {group_expr} as period,
                AVG(metric_value) as avg_value,
                MIN(metric_value) as min_value,
                MAX(metric_value) as max_value,
                COUNT(*) as count
            FROM telemetry_metrics 
            WHERE metric_name = ? AND timestamp >= ?
            GROUP BY period
            ORDER BY period DESC
            """,
            (metric_name, since.isoformat())
        )
        
        return [dict(row) for row in rows]
    
    async def cleanup_old(self, days: int = 30) -> int:
        """Remove metrics older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        return await self.db.delete(
            self.table_name,
            "timestamp < ?",
            (cutoff.isoformat(),)
        )


class ErrorsRepository(BaseRepository[TelemetryError]):
    """Repository for telemetry errors."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "telemetry_errors", TelemetryError)
    
    async def record(
        self,
        error_type: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> int:
        """Record an error."""
        error = TelemetryError(
            error_type=error_type,
            error_code=error_code,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
        )
        return await self.create(error)
    
    async def get_unresolved(self, limit: int = 50) -> list[TelemetryError]:
        """Get unresolved errors."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM telemetry_errors 
            WHERE resolved = 0
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (limit,)
        )
        return [TelemetryError.from_row(row) for row in rows]
    
    async def resolve(self, id: int) -> bool:
        """Mark an error as resolved."""
        count = await self.db.update(
            self.table_name,
            {
                "resolved": 1,
                "resolved_at": datetime.now().isoformat(),
            },
            "id = ?",
            (id,)
        )
        return count > 0
    
    async def get_by_type(
        self,
        error_type: str,
        limit: int = 50,
    ) -> list[TelemetryError]:
        """Get errors by type."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM telemetry_errors 
            WHERE error_type = ?
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (error_type, limit)
        )
        return [TelemetryError.from_row(row) for row in rows]
    
    async def get_error_counts(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, int]:
        """Get error counts by type."""
        if since is None:
            since = datetime.now() - timedelta(days=7)
        
        rows = await self.db.fetch_all(
            """
            SELECT error_type, COUNT(*) as count
            FROM telemetry_errors 
            WHERE timestamp >= ?
            GROUP BY error_type
            ORDER BY count DESC
            """,
            (since.isoformat(),)
        )
        
        return {row["error_type"]: row["count"] for row in rows}


class LogsRepository(BaseRepository[Log]):
    """Repository for logs."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "logs", Log)
    
    async def add(
        self,
        level: str,
        message: str,
        logger_name: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> int:
        """Add a log entry."""
        log = Log(
            level=level,
            message=message,
            logger_name=logger_name,
            context=context or {},
        )
        return await self.create(log)
    
    async def get_by_level(
        self,
        level: str,
        limit: int = 100,
    ) -> list[Log]:
        """Get logs by level."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM logs 
            WHERE level = ?
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (level, limit)
        )
        return [Log.from_row(row) for row in rows]
    
    async def get_recent(
        self,
        limit: int = 100,
        level: Optional[str] = None,
    ) -> list[Log]:
        """Get recent logs."""
        if level:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM logs 
                WHERE level = ?
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (level, limit)
            )
        else:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM logs 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (limit,)
            )
        return [Log.from_row(row) for row in rows]
    
    async def search(
        self,
        query: str,
        limit: int = 100,
    ) -> list[Log]:
        """Search logs by message content."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM logs 
            WHERE message LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        return [Log.from_row(row) for row in rows]
    
    async def cleanup_old(self, days: int = 7) -> int:
        """Remove logs older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        return await self.db.delete(
            self.table_name,
            "timestamp < ?",
            (cutoff.isoformat(),)
        )


class BenchmarksRepository(BaseRepository[Benchmark]):
    """Repository for benchmarks."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "benchmarks", Benchmark)
    
    async def record(
        self,
        session_id: str,
        component: str,
        metric_name: str,
        value: float,
        unit: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Record a benchmark result."""
        benchmark = Benchmark(
            session_id=session_id,
            component=component,
            metric_name=metric_name,
            metric_value=value,
            unit=unit,
            metadata=metadata or {},
        )
        return await self.create(benchmark)
    
    async def get_by_session(self, session_id: str) -> list[Benchmark]:
        """Get benchmarks for a session."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM benchmarks 
            WHERE session_id = ?
            ORDER BY component, metric_name
            """,
            (session_id,)
        )
        return [Benchmark.from_row(row) for row in rows]
    
    async def get_by_component(
        self,
        component: str,
        limit: int = 100,
    ) -> list[Benchmark]:
        """Get benchmarks for a component."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM benchmarks 
            WHERE component = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (component, limit)
        )
        return [Benchmark.from_row(row) for row in rows]
    
    async def get_latest_session(self) -> Optional[str]:
        """Get the most recent benchmark session ID."""
        row = await self.db.fetch_one(
            "SELECT session_id FROM benchmarks ORDER BY timestamp DESC LIMIT 1"
        )
        return row["session_id"] if row else None
    
    async def compare_sessions(
        self,
        session_id_1: str,
        session_id_2: str,
    ) -> dict:
        """Compare benchmarks between two sessions."""
        benchmarks_1 = await self.get_by_session(session_id_1)
        benchmarks_2 = await self.get_by_session(session_id_2)
        
        # Create lookup for session 2
        lookup_2 = {
            (b.component, b.metric_name): b.metric_value
            for b in benchmarks_2
        }
        
        comparison = []
        for b1 in benchmarks_1:
            key = (b1.component, b1.metric_name)
            if key in lookup_2:
                value_2 = lookup_2[key]
                diff = b1.metric_value - value_2
                diff_pct = (diff / value_2 * 100) if value_2 != 0 else 0
                
                comparison.append({
                    "component": b1.component,
                    "metric": b1.metric_name,
                    "session_1_value": b1.metric_value,
                    "session_2_value": value_2,
                    "difference": diff,
                    "difference_pct": diff_pct,
                    "unit": b1.unit,
                })
        
        return {
            "session_1": session_id_1,
            "session_2": session_id_2,
            "comparisons": comparison,
        }