# src/database/repositories/personality_repo.py
"""
Repository for personality fragments and audit log.

Handles all database operations for the personality system:
- CRUD on personality_fragments
- Append-only writes to personality_audit
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from src.database.connection import DatabaseManager
from src.utils.logger import logger


class PersonalityRepository:
    """Data access layer for personality fragments and audit trail."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # Fragment CRUD
    # ──────────────────────────────────────────────────────────────────────────

    async def create_fragment(
        self,
        content: str,
        fragment_type: str = "inferred",
        category: Optional[str] = None,
        confidence: float = 1.0,
        status: str = "pending",
        source: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Insert a new personality fragment.

        Args:
            content: The personality fact / preference text.
            fragment_type: "explicit" (user-stated) or "inferred" (LLM-extracted).
            category: Optional category label (e.g. "preference", "trait", "fact").
            confidence: Confidence score 0-1 (inferred fragments carry this from LLM).
            status: "pending" | "approved" | "rejected".
            source: Short description of where this fragment came from.
            metadata: Arbitrary extra data.

        Returns:
            Dict representation of the created fragment.
        """
        try:
            fragment_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            meta_json = json.dumps(metadata or {})

            await self.db.execute(
                """
                INSERT INTO personality_fragments
                    (fragment_id, content, fragment_type, category, confidence,
                     status, source, version, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (fragment_id, content, fragment_type, category, confidence, status, source, now, now, meta_json),
            )

            logger.info(f"Created personality fragment {fragment_id} ({fragment_type}, status={status})")

            return await self._get_by_fragment_id(fragment_id) or {}

        except Exception as e:
            logger.error(f"Error creating personality fragment: {e}", exc_info=True)
            raise

    async def get_all(
        self,
        status: Optional[str] = None,
        fragment_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch personality fragments with optional filters.

        Args:
            status: Filter by status ("pending", "approved", "rejected").
            fragment_type: Filter by type ("explicit", "inferred").
            category: Filter by category label.
            limit: Max rows to return.
            offset: Pagination offset.

        Returns:
            List of fragment dicts.
        """
        try:
            conditions: list[str] = []
            params: list[Any] = []

            if status:
                conditions.append("status = ?")
                params.append(status)
            if fragment_type:
                conditions.append("fragment_type = ?")
                params.append(fragment_type)
            if category:
                conditions.append("category = ?")
                params.append(category)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.extend([limit, offset])

            rows = await self.db.fetch_all(
                f"""
                SELECT id, fragment_id, content, fragment_type, category,
                       confidence, status, source, version,
                       created_at, updated_at, approved_at, metadata
                FROM personality_fragments
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params),
            )

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching personality fragments: {e}", exc_info=True)
            return []

    async def get_approved(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return all approved fragments, most recent first.

        Args:
            limit: Max fragments to return.

        Returns:
            List of approved fragment dicts.
        """
        return await self.get_all(status="approved", limit=limit)

    async def get_pending(self) -> list[dict[str, Any]]:
        """Return all fragments awaiting approval.

        Returns:
            List of pending fragment dicts.
        """
        return await self.get_all(status="pending")

    async def get_by_id(self, fragment_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single fragment by its UUID.

        Args:
            fragment_id: The UUID string stored in fragment_id column.

        Returns:
            Fragment dict or None if not found.
        """
        return await self._get_by_fragment_id(fragment_id)

    async def update_fragment(
        self,
        fragment_id: str,
        content: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Update mutable fields of a fragment.

        Args:
            fragment_id: UUID of the fragment to update.
            content: New content text (optional).
            status: New status (optional).
            category: New category (optional).
            confidence: New confidence score (optional).
            metadata: Merged metadata (optional).

        Returns:
            True if at least one row was updated.
        """
        try:
            updates: list[str] = ["updated_at = ?"]
            params: list[Any] = [datetime.now().isoformat()]

            if content is not None:
                updates.append("content = ?")
                params.append(content)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
                if status == "approved":
                    updates.append("approved_at = ?")
                    params.append(datetime.now().isoformat())
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            if confidence is not None:
                updates.append("confidence = ?")
                params.append(confidence)
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))

            params.append(fragment_id)

            await self.db.execute(
                f"UPDATE personality_fragments SET {', '.join(updates)} WHERE fragment_id = ?",
                tuple(params),
            )

            logger.info(f"Updated personality fragment {fragment_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating personality fragment {fragment_id}: {e}", exc_info=True)
            return False

    async def delete_fragment(self, fragment_id: str) -> bool:
        """Hard-delete a personality fragment.

        Args:
            fragment_id: UUID of the fragment to delete.

        Returns:
            True on success.
        """
        try:
            await self.db.execute(
                "DELETE FROM personality_fragments WHERE fragment_id = ?",
                (fragment_id,),
            )
            logger.info(f"Deleted personality fragment {fragment_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting personality fragment {fragment_id}: {e}", exc_info=True)
            return False

    async def approve_fragment(self, fragment_id: str) -> bool:
        """Shortcut: set status to 'approved' and record approved_at.

        Args:
            fragment_id: UUID of the fragment to approve.

        Returns:
            True on success.
        """
        return await self.update_fragment(fragment_id, status="approved")

    async def reject_fragment(self, fragment_id: str) -> bool:
        """Shortcut: set status to 'rejected'.

        Args:
            fragment_id: UUID of the fragment to reject.

        Returns:
            True on success.
        """
        return await self.update_fragment(fragment_id, status="rejected")

    # ──────────────────────────────────────────────────────────────────────────
    # Audit log
    # ──────────────────────────────────────────────────────────────────────────

    async def write_audit(
        self,
        fragment_id: str,
        action: str,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        confidence: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Append an entry to the personality audit log.

        Args:
            fragment_id: UUID of the affected fragment.
            action: Human-readable action label (e.g. "approved", "rejected", "inferred", "edited").
            old_content: Previous content before edit (optional).
            new_content: New content after edit (optional).
            old_status: Previous status (optional).
            new_status: New status (optional).
            confidence: Confidence score at time of action (optional).
            reason: Free-text reason for the action (optional).
            metadata: Arbitrary extra context (optional).
        """
        try:
            await self.db.execute(
                """
                INSERT INTO personality_audit
                    (fragment_id, action, old_content, new_content,
                     old_status, new_status, confidence, reason, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fragment_id,
                    action,
                    old_content,
                    new_content,
                    old_status,
                    new_status,
                    confidence,
                    reason,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {}),
                ),
            )
        except Exception as e:
            # Audit failures must never crash the main flow
            logger.warning(f"Failed to write personality audit entry: {e}")

    async def get_audit_log(
        self,
        fragment_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries, optionally filtered by fragment.

        Args:
            fragment_id: If set, return only entries for this fragment UUID.
            limit: Max rows to return.
            offset: Pagination offset.

        Returns:
            List of audit entry dicts (newest first).
        """
        try:
            if fragment_id:
                rows = await self.db.fetch_all(
                    """
                    SELECT id, fragment_id, action, old_content, new_content,
                           old_status, new_status, confidence, reason, timestamp, metadata
                    FROM personality_audit
                    WHERE fragment_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (fragment_id, limit, offset),
                )
            else:
                rows = await self.db.fetch_all(
                    """
                    SELECT id, fragment_id, action, old_content, new_content,
                           old_status, new_status, confidence, reason, timestamp, metadata
                    FROM personality_audit
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            return [self._audit_row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error fetching personality audit log: {e}", exc_info=True)
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about personality fragments.

        Returns:
            Dict with counts by status and type.
        """
        try:
            total_row = await self.db.fetch_one("SELECT COUNT(*) FROM personality_fragments")
            total = total_row[0] if total_row else 0

            status_rows = await self.db.fetch_all("SELECT status, COUNT(*) FROM personality_fragments GROUP BY status")
            by_status = {row[0]: row[1] for row in status_rows} if status_rows else {}

            type_rows = await self.db.fetch_all(
                "SELECT fragment_type, COUNT(*) FROM personality_fragments GROUP BY fragment_type"
            )
            by_type = {row[0]: row[1] for row in type_rows} if type_rows else {}

            return {
                "total": total,
                "by_status": by_status,
                "by_type": by_type,
            }
        except Exception as e:
            logger.error(f"Error fetching personality stats: {e}", exc_info=True)
            return {"total": 0, "by_status": {}, "by_type": {}}

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _get_by_fragment_id(self, fragment_id: str) -> Optional[dict[str, Any]]:
        row = await self.db.fetch_one(
            """
            SELECT id, fragment_id, content, fragment_type, category,
                   confidence, status, source, version,
                   created_at, updated_at, approved_at, metadata
            FROM personality_fragments
            WHERE fragment_id = ?
            """,
            (fragment_id,),
        )
        return self._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        """Map a personality_fragments DB row to a dict."""
        return {
            "id": row[0],
            "fragment_id": row[1],
            "content": row[2],
            "fragment_type": row[3],
            "category": row[4],
            "confidence": row[5],
            "status": row[6],
            "source": row[7],
            "version": row[8],
            "created_at": row[9],
            "updated_at": row[10],
            "approved_at": row[11],
            "metadata": json.loads(row[12]) if row[12] else {},
        }

    @staticmethod
    def _audit_row_to_dict(row: Any) -> dict[str, Any]:
        """Map a personality_audit DB row to a dict."""
        return {
            "id": row[0],
            "fragment_id": row[1],
            "action": row[2],
            "old_content": row[3],
            "new_content": row[4],
            "old_status": row[5],
            "new_status": row[6],
            "confidence": row[7],
            "reason": row[8],
            "timestamp": row[9],
            "metadata": json.loads(row[10]) if row[10] else {},
        }
