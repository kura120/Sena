# src/database/models/conversation.py
"""Conversation model."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Conversation:
    """Represents a conversation turn."""
    
    id: Optional[int] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    user_input: str = ""
    sena_response: str = ""
    model_used: Optional[str] = None
    processing_time_ms: Optional[float] = None
    intent_type: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "sena_response": self.sena_response,
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
            "intent_type": self.intent_type,
            "metadata": self.metadata,
        }
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "sena_response": self.sena_response,
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
            "intent_type": self.intent_type,
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_row(cls, row) -> "Conversation":
        """Create from database row."""
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            user_input=row["user_input"],
            sena_response=row["sena_response"],
            model_used=row["model_used"],
            processing_time_ms=row["processing_time_ms"],
            intent_type=row["intent_type"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )