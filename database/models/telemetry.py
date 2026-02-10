# src/database/models/telemetry.py
"""Telemetry models."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class TelemetryMetric:
    """Telemetry metric entry."""
    
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metric_name: str = ""
    metric_value: float = 0.0
    metric_type: str = "gauge"  # gauge, counter, histogram
    tags: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_type": self.metric_type,
            "tags": self.tags,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_type": self.metric_type,
            "tags": json.dumps(self.tags),
        }
    
    @classmethod
    def from_row(cls, row) -> "TelemetryMetric":
        """Create from database row."""
        return cls(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            metric_name=row["metric_name"],
            metric_value=row["metric_value"],
            metric_type=row["metric_type"],
            tags=json.loads(row["tags"]) if row["tags"] else {},
        )


@dataclass
class TelemetryError:
    """Telemetry error entry."""
    
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: str = ""
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "context": json.dumps(self.context),
            "resolved": 1 if self.resolved else 0,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
    
    @classmethod
    def from_row(cls, row) -> "TelemetryError":
        """Create from database row."""
        return cls(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            error_type=row["error_type"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            stack_trace=row["stack_trace"],
            context=json.loads(row["context"]) if row["context"] else {},
            resolved=bool(row["resolved"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] and isinstance(row["resolved_at"], str) else row["resolved_at"],
        )