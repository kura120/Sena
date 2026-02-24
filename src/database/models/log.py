# src/database/models/log.py
"""Log model."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Log:
    """Log entry."""
    
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "INFO"
    logger_name: Optional[str] = None
    message: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "context": self.context,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "context": json.dumps(self.context),
        }
    
    @classmethod
    def from_row(cls, row) -> "Log":
        """Create from database row."""
        return cls(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            level=row["level"],
            logger_name=row["logger_name"],
            message=row["message"],
            context=json.loads(row["context"]) if row["context"] else {},
        )