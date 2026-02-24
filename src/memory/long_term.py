"""Long-term persistent memory with mem0 integration."""

import json
import re
import uuid
from datetime import datetime
from typing import Any, Optional

import numpy as np
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
        """Search long-term memory by embedding similarity with keyword pre-filter fallback.

        Search strategy (priority order):
        1. If a query embedding is provided, use cosine similarity against stored embeddings.
        2. If no embedding is provided but Ollama is available, generate one on-the-fly.
        3. Keyword/LIKE fallback when embeddings are unavailable.

        Args:
            query: Search query string
            embedding: Pre-computed vector embedding for semantic search (optional)
            k: Number of results to return
            metadata_filter: Optional filter by metadata

        Returns:
            List of matching memories with relevance scores, sorted by relevance descending
        """
        try:
            results = []

            if not self.db:
                logger.warning("No database connection, cannot search")
                return results

            # ── Step 1: Obtain a query embedding ─────────────────────────────
            query_embedding = embedding
            if query_embedding is None:
                query_embedding = await self._try_generate_embedding(query)

            # ── Step 2: Embedding-based search (preferred) ────────────────────
            if query_embedding is not None:
                results = await self._search_by_embedding(
                    query_embedding=query_embedding,
                    k=k * 3,  # Over-fetch so metadata filtering doesn't starve results
                    metadata_filter=metadata_filter,
                )
                # Trim to k after filtering
                results = results[:k]

            # ── Step 3: Keyword fallback when no embedding available ───────────
            if not results:
                logger.debug("Falling back to keyword search (no embedding available)")
                results = await self._search_by_keywords(
                    query=query,
                    k=k,
                    metadata_filter=metadata_filter,
                )

            # ── Step 4: Update access counts ──────────────────────────────────
            for memory in results:
                await self._update_access_count(memory["memory_id"])

            logger.debug(f"Found {len(results)} memories matching '{query}'")
            return results

        except Exception as e:
            logger.error(f"Error searching long-term memory: {e}")
            return []

    async def _try_generate_embedding(self, text: str) -> Optional[list[float]]:
        """Attempt to generate an embedding for a query string.

        Returns None silently if embeddings are unavailable (offline, model not loaded, etc.)

        Args:
            text: Query text to embed.

        Returns:
            Embedding vector or None.
        """
        try:
            from src.memory.embeddings import EmbeddingsHandler

            handler = EmbeddingsHandler()
            return await handler.generate_embedding(text)
        except Exception as e:
            logger.debug(f"Embedding generation unavailable for search: {e}")
            return None

    async def _search_by_embedding(
        self,
        query_embedding: list[float],
        k: int,
        metadata_filter: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """Fetch all stored embeddings and rank by cosine similarity.

        Fetches all rows that have a stored embedding, computes cosine similarity
        in-process with numpy, and returns the top-k results above a minimum
        similarity threshold.

        Args:
            query_embedding: The query vector to compare against.
            k: Number of top results to return.
            metadata_filter: Optional metadata filter dict.

        Returns:
            List of memory dicts sorted by relevance descending.
        """
        MIN_SIMILARITY = 0.30  # Ignore memories with very low similarity

        if not self.db:
            return []

        # Fetch all rows that have a stored embedding
        rows = await self.db.fetch_all(
            """
            SELECT id, content, metadata, access_count, created_at, last_accessed, embedding
            FROM memory_long_term
            WHERE embedding IS NOT NULL
            ORDER BY created_at DESC
            """
        )

        if not rows:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []

        for row in rows:
            try:
                raw_emb = row[6]
                stored_embedding: list[float] = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
                if not stored_embedding:
                    continue

                s_vec = np.array(stored_embedding, dtype=np.float32)
                s_norm = np.linalg.norm(s_vec)
                if s_norm == 0:
                    continue

                similarity = float(np.dot(q_vec, s_vec) / (q_norm * s_norm))
                similarity = max(0.0, min(1.0, similarity))

                if similarity < MIN_SIMILARITY:
                    continue

                metadata = json.loads(row[2]) if row[2] else {}

                if metadata_filter and not self._matches_filter(metadata, metadata_filter):
                    continue

                scored.append(
                    (
                        similarity,
                        {
                            "memory_id": row[0],
                            "content": row[1],
                            "metadata": metadata,
                            "access_count": row[3],
                            "created_at": row[4],
                            "last_accessed": row[5],
                            "relevance": round(similarity, 4),
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Error processing embedding for row {row[0]}: {e}")
                continue

        # Sort by similarity descending and return top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]

    async def _search_by_keywords(
        self,
        query: str,
        k: int,
        metadata_filter: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """Keyword/LIKE based search — used as a fallback when embeddings are unavailable.

        Args:
            query: Raw query string.
            k: Max results.
            metadata_filter: Optional metadata filter.

        Returns:
            List of memory dicts with a static relevance score of 0.5.
        """
        if not self.db:
            return []

        keywords = self._extract_keywords(query)

        if keywords:
            conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in keywords])
            params: list[Any] = [f"%{kw}%" for kw in keywords]
            params.append(k * 2)  # Over-fetch to allow metadata filtering
            rows = await self.db.fetch_all(
                f"""
                SELECT id, content, metadata, access_count, created_at, last_accessed
                FROM memory_long_term
                WHERE {conditions}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                tuple(params),
            )
        else:
            rows = await self.db.fetch_all(
                """
                SELECT id, content, metadata, access_count, created_at, last_accessed
                FROM memory_long_term
                WHERE LOWER(content) LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{query.lower()}%", k * 2),
            )

        results: list[dict[str, Any]] = []
        for row in rows:
            try:
                metadata = json.loads(row[2]) if row[2] else {}
                if metadata_filter and not self._matches_filter(metadata, metadata_filter):
                    continue
                results.append(
                    {
                        "memory_id": row[0],
                        "content": row[1],
                        "metadata": metadata,
                        "access_count": row[3],
                        "created_at": row[4],
                        "last_accessed": row[5],
                        "relevance": 0.5,  # Neutral score for keyword matches
                    }
                )
            except Exception as e:
                logger.warning(f"Error parsing memory row: {e}")
                continue

        return results[:k]

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

    @staticmethod
    def _extract_keywords(query: str) -> list[str]:
        """Extract meaningful search keywords from a natural-language query.

        Strips common English stop-words and question words so that a query
        like "what number did I tell you to remember?" reduces to ["number"],
        which can then match a stored memory like "number: 6".

        Args:
            query: The raw search query string.

        Returns:
            List of lowercase keywords (may be empty if nothing meaningful left).
        """
        stop_words = {
            # articles / prepositions
            "a",
            "an",
            "the",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
            "from",
            "into",
            "about",
            "as",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            # pronouns
            "i",
            "me",
            "my",
            "we",
            "us",
            "our",
            "you",
            "your",
            "he",
            "she",
            "it",
            "they",
            "them",
            "their",
            # question / recall words — don't use as search terms
            "what",
            "which",
            "who",
            "whom",
            "where",
            "when",
            "why",
            "how",
            "tell",
            "told",
            "said",
            "say",
            "ask",
            "asked",
            "remember",
            "recall",
            "forget",
            "know",
            "knew",
            # filler
            "that",
            "this",
            "these",
            "those",
            "and",
            "or",
            "but",
            "not",
            "no",
            "so",
            "if",
            "then",
            "than",
            "there",
            "here",
            "just",
            "also",
            "already",
            "still",
            "again",
            "back",
            "up",
            "down",
            "out",
            "please",
            "let",
            "make",
        }

        words = re.findall(r"[a-zA-Z0-9]+", query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique

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
