# src/database/models/memory.py
"""Memory models."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MemoryShortTerm:
    """Short-term memory entry (session buffer)."""
    
    id: Optional[int] = None
    session_id: str = ""
    content: str = ""
    role: str = "user"  # user, assistant, system
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "metadata": self.metadata,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "session_id": self.session_id,
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_row(cls, row: Any) -> "MemoryShortTerm":
        """Create from database row."""
        timestamp = row["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        elif metadata is None:
            metadata = {}
        
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            content=row["content"],
            role=row["role"],
            timestamp=timestamp,
            metadata=metadata,
        )


@dataclass
class MemoryLongTerm:
    """Long-term memory entry (persistent)."""
    
    id: Optional[int] = None
    memory_id: str = ""
    content: str = ""
    category: Optional[str] = None
    importance: int = 5
    embedding: Optional[bytes] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Runtime fields (not stored in DB)
    relevance_score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed and isinstance(self.last_accessed, datetime) else None,
            "metadata": self.metadata,
            "relevance_score": self.relevance_score,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed and isinstance(self.last_accessed, datetime) else None,
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_row(cls, row: Any) -> "MemoryLongTerm":
        """Create from database row."""
        def parse_datetime(val: Any) -> Optional[datetime]:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return None
        
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        elif metadata is None:
            metadata = {}
        
        return cls(
            id=row["id"],
            memory_id=row["memory_id"],
            content=row["content"],
            category=row["category"],
            importance=row["importance"],
            embedding=row["embedding"],
            created_at=parse_datetime(row["created_at"]) or datetime.now(),
            updated_at=parse_datetime(row["updated_at"]) or datetime.now(),
            access_count=row["access_count"],
            last_accessed=parse_datetime(row["last_accessed"]),
            metadata=metadata,
        )