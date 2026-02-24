# src/database/models/benchmark.py
"""Benchmark model."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Benchmark:
    """Benchmark result."""
    
    id: Optional[int] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    unit: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "metadata": self.metadata,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_row(cls, row) -> "Benchmark":
        """Create from database row."""
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            component=row["component"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
            unit=row["unit"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )