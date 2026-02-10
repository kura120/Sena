# src/database/models/extension.py
"""Extension model."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Extension:
    """Extension metadata."""
    
    id: Optional[int] = None
    name: str = ""
    version: str = "1.0.0"
    file_path: str = ""
    extension_type: str = "user"  # core, user, generated
    status: str = "active"  # active, inactive, error
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_loaded: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    avg_execution_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "file_path": self.file_path,
            "extension_type": self.extension_type,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "avg_execution_ms": self.avg_execution_ms,
            "metadata": self.metadata,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "name": self.name,
            "version": self.version,
            "file_path": self.file_path,
            "extension_type": self.extension_type,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "avg_execution_ms": self.avg_execution_ms,
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_row(cls, row) -> "Extension":
        """Create from database row."""
        return cls(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            file_path=row["file_path"],
            extension_type=row["extension_type"],
            status=row["status"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            last_loaded=datetime.fromisoformat(row["last_loaded"]) if row["last_loaded"] and isinstance(row["last_loaded"], str) else row["last_loaded"],
            execution_count=row["execution_count"],
            error_count=row["error_count"],
            avg_execution_ms=row["avg_execution_ms"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )