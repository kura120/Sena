"""Long-term persistent memory with mem0 integration."""

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from loguru import logger
from pydantic import BaseModel

from src.database.connection import DatabaseManager


class LongTermMemory:
    """Persistent memory storage integrated with mem0 and SQLite.

    - Stores learnings extracted from conversations
    - Persists across sessions
    - Searchable via vector embeddings
    """

    def __init__(self, db_connection: Optional[DatabaseManager] = None):
        """Initialize long-term memory.

        Args:
            db_connection: Database manager instance
        """
        self.db = db_connection

    async def add(
        self, content: str, metadata: Optional[dict] = None, embedding: Optional[list[float]] = None
    ) -> dict[str, Any]:
        """Store new memory in long-term storage.

        Args:
            content: Memory content/learning
            metadata: Optional metadata (tags, source, etc)
            embedding: Vector embedding for semantic search

        Returns:
            Dictionary with memory_id and details
        """
        try:
            if not content or not content.strip():
                raise ValueError("Memory content cannot be empty")

            now = datetime.now().isoformat()
            memory_id = str(uuid.uuid4())

            memory_data = {
                "content": content,
                "metadata": metadata or {},
                "embedding": embedding or None,
                "created_at": now,
                "access_count": 0,
                "last_accessed": None,
            }

            if self.db:
                # Store in database
                await self.db.execute(
                    """
                    INSERT INTO memory_long_term
                    (memory_id, content, metadata, embedding, created_at, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory_id,
                        content,
                        json.dumps(metadata or {}),
                        json.dumps(embedding) if embedding else None,
                        now,
                        0,
                        None,
                    ),
                )
                logger.info(f"Stored long-term memory: {memory_id}")

                return {"memory_id": memory_id, "content": content, "created_at": now, "status": "stored"}
            else:
                logger.warning("No database connection, memory not persisted")
                return {"memory_id": None, "content": content, "created_at": now, "status": "not_stored"}

        except Exception as e:
            logger.error(f"Error storing long-term memory: {e}")
            raise

    async def search(
        self, query: str, embedding: Optional[list[float]] = None, k: int = 5, metadata_filter: Optional[dict] = None
    ) -> list[dict[str, Any]]:
        """Search long-term memory by content or embedding.

        Args:
            query: Search query string
            embedding: Vector embedding for semantic search
            k: Number of results to return
            metadata_filter: Optional filter by metadata

        Returns:
            List of matching memories with relevance scores
        """
        try:
            results = []

            if not self.db:
                logger.warning("No database connection, cannot search")
                return results

            # For now, do simple text search (production would use vector similarity)
            # This is a basic implementation
            query_lower = query.lower()

            rows = await self.db.fetch_all(
                """
                SELECT id, content, metadata, access_count, created_at, last_accessed
                FROM memory_long_term
                WHERE content LIKE ?
                LIMIT ?
                """,
                (f"%{query_lower}%", k),
            )

            for row in rows:
                try:
                    metadata = json.loads(row[2]) if row[2] else {}

                    # Check metadata filter if provided
                    if metadata_filter:
                        if not self._matches_filter(metadata, metadata_filter):
                            continue

                    results.append(
                        {
                            "memory_id": row[0],
                            "content": row[1],
                            "metadata": metadata,
                            "access_count": row[3],
                            "created_at": row[4],
                            "last_accessed": row[5],
                            "relevance": 0.8,  # Placeholder score
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error parsing memory row: {e}")
                    continue

            # Update access count for retrieved memories
            for memory in results:
                await self._update_access_count(memory["memory_id"])

            logger.debug(f"Found {len(results)} memories matching '{query}'")
            return results

        except Exception as e:
            logger.error(f"Error searching long-term memory: {e}")
            return []

    async def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent memories ordered by creation time."""
        try:
            if not self.db:
                logger.warning("No database connection, cannot fetch recent memories")
                return []

            rows = await self.db.fetch_all(
                """
                SELECT id, content, metadata, access_count, created_at, last_accessed
                FROM memory_long_term
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            results = []
            for row in rows:
                try:
                    metadata = json.loads(row[2]) if row[2] else {}
                    results.append(
                        {
                            "memory_id": row[0],
                            "content": row[1],
                            "metadata": metadata,
                            "access_count": row[3],
                            "created_at": row[4],
                            "last_accessed": row[5],
                            "relevance": 1.0,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error parsing recent memory row: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Error fetching recent memories: {e}")
            return []

    async def update(self, memory_id: int, content: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
        """Update existing memory.

        Args:
            memory_id: ID of memory to update
            content: Updated content (optional)
            metadata: Updated metadata (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.db:
                return False

            updates = []
            params = []

            if content is not None:
                updates.append("content = ?")
                params.append(content)

            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))

            if not updates:
                logger.warning("No updates specified for memory")
                return False

            updates.append("last_accessed = ?")
            params.append(datetime.now().isoformat())
            params.append(memory_id)

            query = f"UPDATE memory_long_term SET {', '.join(updates)} WHERE id = ?"
            await self.db.execute(query, tuple(params))

            logger.info(f"Updated long-term memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating long-term memory: {e}")
            return False

    async def delete(self, memory_id: int) -> bool:
        """Delete memory by ID.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.db:
                return False

            await self.db.execute("DELETE FROM memory_long_term WHERE id = ?", (memory_id,))

            logger.info(f"Deleted long-term memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting long-term memory: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about long-term memory.

        Returns:
            Dictionary with memory statistics
        """
        try:
            if not self.db:
                return {"error": "No database connection"}

            count = await self.db.fetch_one("SELECT COUNT(*) FROM memory_long_term")

            most_accessed = await self.db.fetch_all(
                """
                SELECT id, content, access_count
                FROM memory_long_term
                ORDER BY access_count DESC
                LIMIT 5
                """
            )

            recent = await self.db.fetch_all(
                """
                SELECT id, content, created_at
                FROM memory_long_term
                ORDER BY created_at DESC
                LIMIT 5
                """
            )

            return {
                "total_memories": count[0] if count else 0,
                "most_accessed": [{"id": m[0], "content": m[1][:100], "accesses": m[2]} for m in most_accessed]
                if most_accessed
                else [],
                "recent": [{"id": m[0], "content": m[1][:100], "created_at": m[2]} for m in recent] if recent else [],
            }

        except Exception as e:
            logger.error(f"Error getting long-term memory stats: {e}")
            return {"error": str(e)}

    def _matches_filter(self, metadata: dict, filter_dict: dict) -> bool:
        """Check if metadata matches filter criteria.

        Args:
            metadata: Memory metadata
            filter_dict: Filter criteria

        Returns:
            True if all filter criteria match
        """
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

    async def _update_access_count(self, memory_id: int) -> None:
        """Update access count and timestamp for memory.

        Args:
            memory_id: ID of memory to update
        """
        try:
            if not self.db:
                return

            await self.db.execute(
                """
                UPDATE memory_long_term
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), memory_id),
            )
        except Exception as e:
            logger.warning(f"Error updating access count: {e}")
