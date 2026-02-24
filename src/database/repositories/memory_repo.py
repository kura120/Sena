# src/database/repositories/memory_repo.py
"""Memory repository."""

from datetime import datetime
from typing import Any, Optional
import uuid

from src.database.connection import DatabaseManager
from src.database.models.memory import MemoryShortTerm, MemoryLongTerm
from src.database.repositories.base import BaseRepository


class MemoryRepository:
    """Repository for memory operations."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.short_term = ShortTermMemoryRepository(db)
        self.long_term = LongTermMemoryRepository(db)


class ShortTermMemoryRepository(BaseRepository[MemoryShortTerm]):
    """Repository for short-term memory operations."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "memory_short_term", MemoryShortTerm)
    
    async def get_session_buffer(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[MemoryShortTerm]:
        """Get the short-term buffer for a session."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM memory_short_term 
            WHERE session_id = ? 
            ORDER BY timestamp ASC 
            LIMIT ?
            """,
            (session_id, limit)
        )
        return [MemoryShortTerm.from_row(row) for row in rows]
    
    async def add_message(
        self,
        session_id: str,
        content: str,
        role: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Add a message to the short-term buffer."""
        memory = MemoryShortTerm(
            session_id=session_id,
            content=content,
            role=role,
            metadata=metadata or {},
        )
        return await self.create(memory)
    
    async def clear_session(self, session_id: str) -> int:
        """Clear all short-term memory for a session."""
        return await self.db.delete(
            self.table_name,
            "session_id = ?",
            (session_id,)
        )
    
    async def cleanup_expired(self, expire_seconds: int = 3600) -> int:
        """Remove expired short-term memories."""
        cutoff = datetime.now().timestamp() - expire_seconds
        return await self.db.delete(
            self.table_name,
            "timestamp < datetime(?, 'unixepoch')",
            (cutoff,)
        )


class LongTermMemoryRepository(BaseRepository[MemoryLongTerm]):
    """Repository for long-term memory operations."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "memory_long_term", MemoryLongTerm)
    
    async def get_by_memory_id(self, memory_id: str) -> Optional[MemoryLongTerm]:
        """Get a memory by its unique ID."""
        row = await self.db.fetch_one(
            "SELECT * FROM memory_long_term WHERE memory_id = ?",
            (memory_id,)
        )
        return MemoryLongTerm.from_row(row) if row else None
    
    async def add_memory(
        self,
        content: str,
        category: Optional[str] = None,
        importance: int = 5,
        embedding: Optional[bytes] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add a new long-term memory."""
        memory_id = str(uuid.uuid4())
        memory = MemoryLongTerm(
            memory_id=memory_id,
            content=content,
            category=category,
            importance=importance,
            embedding=embedding,
            metadata=metadata or {},
        )
        await self.create(memory)
        return memory_id
    
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[int] = None,
        embedding: Optional[bytes] = None,
    ) -> bool:
        """Update an existing memory."""
        updates: dict[str, Any] = {"updated_at": datetime.now().isoformat()}
        
        if content is not None:
            updates["content"] = content
        if importance is not None:
            updates["importance"] = importance
        if embedding is not None:
            updates["embedding"] = embedding
        
        count = await self.db.update(
            self.table_name,
            updates,
            "memory_id = ?",
            (memory_id,)
        )
        return count > 0
    
    async def record_access(self, memory_id: str) -> bool:
        """Record that a memory was accessed."""
        # Can't use SQL expression in dict, need raw query
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE memory_long_term 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE memory_id = ?
                """,
                (datetime.now().isoformat(), memory_id)
            )
            await conn.commit()
            return cursor.rowcount > 0
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 50,
    ) -> list[MemoryLongTerm]:
        """Get memories by category."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM memory_long_term 
            WHERE category = ? 
            ORDER BY importance DESC, created_at DESC 
            LIMIT ?
            """,
            (category, limit)
        )
        return [MemoryLongTerm.from_row(row) for row in rows]
    
    async def get_important(
        self,
        min_importance: int = 7,
        limit: int = 50,
    ) -> list[MemoryLongTerm]:
        """Get high-importance memories."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM memory_long_term 
            WHERE importance >= ? 
            ORDER BY importance DESC, access_count DESC 
            LIMIT ?
            """,
            (min_importance, limit)
        )
        return [MemoryLongTerm.from_row(row) for row in rows]
    
    async def search_text(
        self,
        query: str,
        limit: int = 20,
    ) -> list[MemoryLongTerm]:
        """Search memories by text content."""
        rows = await self.db.fetch_all(
            """
            SELECT * FROM memory_long_term 
            WHERE content LIKE ? 
            ORDER BY importance DESC, access_count DESC 
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        return [MemoryLongTerm.from_row(row) for row in rows]
    
    async def delete_by_memory_id(self, memory_id: str) -> bool:
        """Delete a memory by its ID."""
        count = await self.db.delete(
            self.table_name,
            "memory_id = ?",
            (memory_id,)
        )
        return count > 0
    
    async def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        total = await self.count()
        
        # Get category distribution
        rows = await self.db.fetch_all(
            """
            SELECT category, COUNT(*) as count 
            FROM memory_long_term 
            GROUP BY category
            """
        )
        categories = {row["category"] or "uncategorized": row["count"] for row in rows}
        
        # Get average importance
        row = await self.db.fetch_one(
            "SELECT AVG(importance) as avg FROM memory_long_term"
        )
        avg_importance = row["avg"] if row and row["avg"] else 0
        
        return {
            "total_memories": total,
            "categories": categories,
            "avg_importance": avg_importance,
        }