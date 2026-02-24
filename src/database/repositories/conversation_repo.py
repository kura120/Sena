# src/database/repositories/conversation_repo.py
"""Conversation repository."""

from datetime import datetime
from typing import Optional

from src.database.connection import DatabaseManager
from src.database.models.conversation import Conversation
from src.database.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "conversations", Conversation)
    
    async def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get conversations for a session."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM conversations 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (session_id, limit)
        )
        return [Conversation.from_row(row) for row in rows]
    
    async def get_recent(
        self,
        limit: int = 10,
        session_id: Optional[str] = None,
    ) -> list[Conversation]:
        """Get recent conversations."""
        if session_id:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM conversations 
                WHERE session_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (session_id, limit)
            )
        else:
            rows = await self.db.fetch_all(
                """
                SELECT * FROM conversations 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (limit,)
            )
        return [Conversation.from_row(row) for row in rows]
    
    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Conversation]:
        """Search conversations by content."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM conversations 
            WHERE user_input LIKE ? OR sena_response LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        )
        return [Conversation.from_row(row) for row in rows]
    
    async def get_stats(self) -> dict:
        """Get conversation statistics."""
        total = await self.count()
        
        # Get session count
        row = await self.db.fetch_one(
            "SELECT COUNT(DISTINCT session_id) as count FROM conversations"
        )
        session_count = row["count"] if row else 0
        
        # Get average processing time
        row = await self.db.fetch_one(
            "SELECT AVG(processing_time_ms) as avg_time FROM conversations WHERE processing_time_ms IS NOT NULL"
        )
        avg_processing_time = row["avg_time"] if row and row["avg_time"] else 0
        
        return {
            "total_conversations": total,
            "total_sessions": session_count,
            "avg_processing_time_ms": avg_processing_time,
        }