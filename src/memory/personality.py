# src/memory/personality.py
"""
Personality Manager

Manages Sena's understanding of the user's personality, preferences, and personal facts.

Architecture:
- Fragments are stored in DB (personality_fragments table) via PersonalityRepository
- "explicit" fragments: user directly stated something ("I prefer dark mode")
- "inferred" fragments: LLM extracted from conversation context
- Inferred fragments start as "pending" and require approval (configurable auto-approve)
- Approved fragments are injected into the system prompt via build_personality_block()
- When fragment count exceeds compress_threshold, they are summarized into a compact block

Flow:
    User conversation
        ↓
    infer_from_conversation()  ← runs after N messages
        ↓
    Fragments created as "pending"
        ↓
    [auto-approve if confidence >= threshold AND auto_approve_enabled]
        OR
    [user reviews via UI → approve/reject]
        ↓
    get_personality_block()  ← called by sena.py for every LLM request
        ↓
    Injected into system prompt
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Optional

from src.utils.logger import logger


class PersonalityManager:
    """Orchestrate personality fragment storage, inference, and system prompt composition."""

    _instance: Optional["PersonalityManager"] = None

    def __init__(self) -> None:
        self._repo: Optional[Any] = None  # PersonalityRepository, set during initialize()
        self._llm_manager: Optional[Any] = None  # LLMManager, set during initialize()
        self._settings: Optional[Any] = None
        self._initialized: bool = False

        # In-memory cache of the approved personality block to avoid DB round-trips on
        # every single LLM request. Invalidated whenever a fragment is approved/rejected.
        self._block_cache: Optional[str] = None
        self._cache_dirty: bool = True

    # ──────────────────────────────────────────────────────────────────────────
    # Singleton
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "PersonalityManager":
        """Return the singleton PersonalityManager, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "PersonalityManager") -> None:
        """Override the singleton (useful for testing)."""
        cls._instance = instance

    # ──────────────────────────────────────────────────────────────────────────
    # Initialization
    # ──────────────────────────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the manager: wire up DB repository, LLM manager, and settings.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            return True

        try:
            from src.config.settings import get_settings
            from src.database.connection import get_db
            from src.database.repositories.personality_repo import PersonalityRepository
            from src.llm.manager import LLMManager

            self._settings = get_settings()
            db = await get_db()
            self._repo = PersonalityRepository(db)
            self._llm_manager = LLMManager()

            self._initialized = True
            self._cache_dirty = True
            logger.info("PersonalityManager initialized")
            return True

        except Exception as e:
            logger.error(f"PersonalityManager initialization failed: {e}", exc_info=True)
            return False

    def _get_personality_config(self) -> Any:
        """Return personality config, reloading settings if needed."""
        if self._settings is None:
            from src.config.settings import get_settings

            self._settings = get_settings()
        return self._settings.memory.personality

    # ──────────────────────────────────────────────────────────────────────────
    # System Prompt Composition
    # ──────────────────────────────────────────────────────────────────────────

    async def get_personality_block(self, force_refresh: bool = False) -> str:
        """Return the personality block string ready for injection into the system prompt.

        Uses an in-memory cache that is invalidated whenever fragments change.
        If there are many approved fragments, they are compressed via LLM before caching.

        Args:
            force_refresh: If True, bypass cache and rebuild from DB.

        Returns:
            Formatted personality block string.
        """
        from src.llm.prompts.personality_prompts import build_personality_block

        if not self._cache_dirty and not force_refresh and self._block_cache is not None:
            return self._block_cache

        try:
            if not self._repo:
                return build_personality_block(None)

            cfg = self._get_personality_config()
            approved = await self._repo.get_approved(limit=cfg.max_fragments_in_prompt * 2)

            if not approved:
                block = build_personality_block(None)
            elif len(approved) > cfg.compress_threshold:
                # Compress via LLM when there are many fragments
                content = await self._compress_fragments(approved, cfg.personality_token_budget)
                block = build_personality_block(content)
            else:
                # Cap to max_fragments_in_prompt and format as bullet list
                capped = approved[: cfg.max_fragments_in_prompt]
                lines = [f"- {f['content']}" for f in capped]
                block = build_personality_block("\n".join(lines))

            self._block_cache = block
            self._cache_dirty = False
            return block

        except Exception as e:
            logger.error(f"Error building personality block: {e}", exc_info=True)
            from src.llm.prompts.personality_prompts import build_personality_block

            return build_personality_block(None)

    def invalidate_cache(self) -> None:
        """Mark the block cache as stale so the next call rebuilds from DB."""
        self._cache_dirty = True
        self._block_cache = None

    # ──────────────────────────────────────────────────────────────────────────
    # Explicit Fragment Storage (user-stated facts)
    # ──────────────────────────────────────────────────────────────────────────

    async def store_explicit(
        self,
        content: str,
        category: Optional[str] = None,
        source: Optional[str] = "user_input",
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Store a user-explicitly-stated personality fact as immediately approved.

        Explicit fragments skip the approval queue because the user directly stated the fact.

        Args:
            content: The personality fact text.
            category: Optional category (e.g. "preference", "fact").
            source: Where this came from (default: "user_input").
            metadata: Optional extra context.

        Returns:
            The created fragment dict.
        """
        if not self._repo:
            logger.warning("PersonalityManager not initialized; cannot store explicit fragment")
            return {}

        try:
            fragment = await self._repo.create_fragment(
                content=content,
                fragment_type="explicit",
                category=category,
                confidence=1.0,
                status="approved",  # Explicit = immediately approved
                source=source,
                metadata=metadata,
            )

            await self._repo.write_audit(
                fragment_id=fragment["fragment_id"],
                action="explicit_stored",
                new_content=content,
                new_status="approved",
                confidence=1.0,
                reason="User explicitly stated this fact",
            )

            self.invalidate_cache()
            logger.info(f"Stored explicit personality fragment: {fragment['fragment_id']}")
            return fragment

        except Exception as e:
            logger.error(f"Error storing explicit personality fragment: {e}", exc_info=True)
            return {}

    # ──────────────────────────────────────────────────────────────────────────
    # Inference (LLM-extracted from conversation)
    # ──────────────────────────────────────────────────────────────────────────

    async def infer_from_conversation(
        self,
        conversation: str,
        source: Optional[str] = "conversation_extraction",
    ) -> list[dict[str, Any]]:
        """Run LLM inference to extract personality fragments from a conversation.

        Extracted fragments start as "pending" unless auto-approve policy allows them
        to be immediately approved.

        Args:
            conversation: Full conversation text (user + assistant turns).
            source: Label describing the extraction source.

        Returns:
            List of created fragment dicts (may include pending + auto-approved).
        """
        if not self._repo or not self._llm_manager:
            logger.warning("PersonalityManager not fully initialized; skipping inference")
            return []

        cfg = self._get_personality_config()
        if not cfg.inferential_learning_enabled:
            logger.debug("Inferential learning disabled; skipping personality inference")
            return []

        try:
            # Get known approved fragments to avoid duplicates in the prompt
            known = await self._repo.get_approved(limit=50)
            known_contents = [f["content"] for f in known]

            # Build and call the inference prompt
            from src.llm.prompts.personality_prompts import build_inference_prompt

            prompt = build_inference_prompt(conversation=conversation, known_fragments=known_contents)

            raw = await self._llm_manager.generate_simple(
                prompt=prompt,
                max_tokens=512,
            )

            if not raw or not raw.strip():
                logger.debug("LLM returned empty response for personality inference")
                return []

            # Parse JSON array from LLM response
            candidates = self._parse_inference_response(raw)

            if not candidates:
                logger.debug("No personality candidates extracted from conversation")
                return []

            created: list[dict[str, Any]] = []

            for candidate in candidates:
                content = candidate.get("content", "").strip()
                confidence = float(candidate.get("confidence", 0.0))
                category = candidate.get("category", "preference")

                if not content or confidence < 0.5:
                    continue

                # Determine initial status based on auto-approve policy
                status = self._decide_initial_status(confidence, cfg)

                fragment = await self._repo.create_fragment(
                    content=content,
                    fragment_type="inferred",
                    category=category,
                    confidence=confidence,
                    status=status,
                    source=source,
                    metadata={"inferred_at": datetime.now().isoformat()},
                )

                await self._repo.write_audit(
                    fragment_id=fragment["fragment_id"],
                    action="inferred",
                    new_content=content,
                    new_status=status,
                    confidence=confidence,
                    reason=f"LLM inference (confidence={confidence:.2f})",
                )

                if status == "approved":
                    logger.info(
                        f"Auto-approved inferred fragment (confidence={confidence:.2f}): {fragment['fragment_id']}"
                    )
                    self.invalidate_cache()
                else:
                    logger.info(
                        f"Inferred fragment pending approval (confidence={confidence:.2f}): {fragment['fragment_id']}"
                    )

                created.append(fragment)

            return created

        except Exception as e:
            logger.error(f"Error during personality inference: {e}", exc_info=True)
            return []

    def _decide_initial_status(self, confidence: float, cfg: Any) -> str:
        """Determine the initial status for an inferred fragment.

        Args:
            confidence: LLM confidence score for this fragment.
            cfg: PersonalityConfig instance.

        Returns:
            "approved" if auto-approve policy allows, otherwise "pending".
        """
        if (
            cfg.auto_approve_enabled
            and not cfg.inferential_learning_requires_approval
            and confidence >= cfg.auto_approve_threshold
        ):
            return "approved"
        return "pending"

    def _parse_inference_response(self, raw: str) -> list[dict[str, Any]]:
        """Safely parse the LLM's JSON array response for personality inference.

        Handles cases where the LLM wraps the JSON in markdown code fences or adds
        extra text before/after the array.

        Args:
            raw: Raw string response from the LLM.

        Returns:
            List of candidate dicts, or empty list on parse failure.
        """
        # Strip markdown code fences if present
        text = raw.strip()
        # Remove ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        text = text.strip()

        # Find the JSON array (in case there's preamble text)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)

        try:
            candidates = json.loads(text)
            if not isinstance(candidates, list):
                logger.warning("Personality inference response was not a JSON array")
                return []
            return candidates
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse personality inference JSON: {e}\nRaw: {raw[:300]}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Approval / Rejection
    # ──────────────────────────────────────────────────────────────────────────

    async def approve_fragment(self, fragment_id: str, reason: Optional[str] = None) -> bool:
        """Approve a pending personality fragment.

        Args:
            fragment_id: UUID of the fragment to approve.
            reason: Optional human-readable reason.

        Returns:
            True on success.
        """
        if not self._repo:
            return False

        try:
            fragment = await self._repo.get_by_id(fragment_id)
            if not fragment:
                logger.warning(f"Fragment not found for approval: {fragment_id}")
                return False

            old_status = fragment["status"]
            success = await self._repo.approve_fragment(fragment_id)

            if success:
                await self._repo.write_audit(
                    fragment_id=fragment_id,
                    action="approved",
                    old_content=fragment["content"],
                    new_content=fragment["content"],
                    old_status=old_status,
                    new_status="approved",
                    confidence=fragment["confidence"],
                    reason=reason or "User approved",
                )
                self.invalidate_cache()
                logger.info(f"Approved personality fragment: {fragment_id}")

                # Emit WebSocket event
                await self._broadcast_personality_update("approved", fragment_id, fragment["content"])

            return success

        except Exception as e:
            logger.error(f"Error approving fragment {fragment_id}: {e}", exc_info=True)
            return False

    async def reject_fragment(self, fragment_id: str, reason: Optional[str] = None) -> bool:
        """Reject a pending personality fragment.

        Args:
            fragment_id: UUID of the fragment to reject.
            reason: Optional human-readable reason.

        Returns:
            True on success.
        """
        if not self._repo:
            return False

        try:
            fragment = await self._repo.get_by_id(fragment_id)
            if not fragment:
                logger.warning(f"Fragment not found for rejection: {fragment_id}")
                return False

            old_status = fragment["status"]
            success = await self._repo.reject_fragment(fragment_id)

            if success:
                await self._repo.write_audit(
                    fragment_id=fragment_id,
                    action="rejected",
                    old_content=fragment["content"],
                    new_content=fragment["content"],
                    old_status=old_status,
                    new_status="rejected",
                    confidence=fragment["confidence"],
                    reason=reason or "User rejected",
                )
                # No cache invalidation needed; rejected fragments don't appear in the block
                logger.info(f"Rejected personality fragment: {fragment_id}")

                await self._broadcast_personality_update("rejected", fragment_id, fragment["content"])

            return success

        except Exception as e:
            logger.error(f"Error rejecting fragment {fragment_id}: {e}", exc_info=True)
            return False

    async def edit_and_approve(
        self,
        fragment_id: str,
        new_content: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Edit a fragment's content and immediately approve it.

        Useful for correcting slightly-wrong inferred facts before approving.

        Args:
            fragment_id: UUID of the fragment to edit.
            new_content: Corrected content text.
            reason: Optional reason for the edit.

        Returns:
            True on success.
        """
        if not self._repo:
            return False

        try:
            fragment = await self._repo.get_by_id(fragment_id)
            if not fragment:
                logger.warning(f"Fragment not found for edit: {fragment_id}")
                return False

            success = await self._repo.update_fragment(
                fragment_id,
                content=new_content,
                status="approved",
            )

            if success:
                await self._repo.write_audit(
                    fragment_id=fragment_id,
                    action="edited_and_approved",
                    old_content=fragment["content"],
                    new_content=new_content,
                    old_status=fragment["status"],
                    new_status="approved",
                    confidence=fragment["confidence"],
                    reason=reason or "User edited and approved",
                )
                self.invalidate_cache()
                logger.info(f"Edited and approved personality fragment: {fragment_id}")
                await self._broadcast_personality_update("approved", fragment_id, new_content)

            return success

        except Exception as e:
            logger.error(f"Error editing fragment {fragment_id}: {e}", exc_info=True)
            return False

    async def delete_fragment(self, fragment_id: str) -> bool:
        """Permanently delete a personality fragment.

        Args:
            fragment_id: UUID of the fragment to delete.

        Returns:
            True on success.
        """
        if not self._repo:
            return False

        try:
            fragment = await self._repo.get_by_id(fragment_id)
            if not fragment:
                return False

            success = await self._repo.delete_fragment(fragment_id)

            if success:
                await self._repo.write_audit(
                    fragment_id=fragment_id,
                    action="deleted",
                    old_content=fragment["content"],
                    old_status=fragment["status"],
                    reason="User deleted fragment",
                )
                self.invalidate_cache()
                logger.info(f"Deleted personality fragment: {fragment_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting fragment {fragment_id}: {e}", exc_info=True)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Query / Stats
    # ──────────────────────────────────────────────────────────────────────────

    async def get_all_fragments(
        self,
        status: Optional[str] = None,
        fragment_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return fragments with optional filters.

        Args:
            status: Filter by "pending", "approved", or "rejected".
            fragment_type: Filter by "explicit" or "inferred".
            limit: Max results.

        Returns:
            List of fragment dicts.
        """
        if not self._repo:
            return []
        return await self._repo.get_all(status=status, fragment_type=fragment_type, limit=limit)

    async def get_pending_fragments(self) -> list[dict[str, Any]]:
        """Return all pending (awaiting approval) fragments.

        Returns:
            List of pending fragment dicts.
        """
        if not self._repo:
            return []
        return await self._repo.get_pending()

    async def get_audit_log(
        self,
        fragment_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return audit log entries.

        Args:
            fragment_id: If set, return only entries for this fragment.
            limit: Max results.

        Returns:
            List of audit entry dicts.
        """
        if not self._repo:
            return []
        return await self._repo.get_audit_log(fragment_id=fragment_id, limit=limit)

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate stats about personality fragments.

        Returns:
            Dict with counts by status, type, and a pending count for UI badges.
        """
        if not self._repo:
            return {"total": 0, "by_status": {}, "by_type": {}, "pending_count": 0}

        stats = await self._repo.get_stats()
        stats["pending_count"] = stats.get("by_status", {}).get("pending", 0)
        return stats

    async def get_preview_block(self) -> str:
        """Return a fresh (non-cached) personality block for UI preview.

        Returns:
            Formatted personality block string.
        """
        return await self.get_personality_block(force_refresh=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Compression
    # ──────────────────────────────────────────────────────────────────────────

    async def _compress_fragments(
        self,
        fragments: list[dict[str, Any]],
        target_tokens: int = 400,
    ) -> str:
        """Use the LLM to compress many fragments into a concise summary.

        Falls back to a simple bullet list if LLM compression fails.

        Args:
            fragments: List of approved fragment dicts.
            target_tokens: Approximate token budget for the compressed output.

        Returns:
            Compressed summary string.
        """
        if not self._llm_manager:
            # Fallback: plain bullet list (truncated)
            lines = [f"- {f['content']}" for f in fragments[:20]]
            return "\n".join(lines)

        try:
            from src.llm.prompts.personality_prompts import build_compression_prompt

            contents = [f["content"] for f in fragments]
            prompt = build_compression_prompt(fragments=contents, target_tokens=target_tokens)

            compressed = await self._llm_manager.generate_simple(
                prompt=prompt,
                max_tokens=target_tokens,
            )

            if compressed and compressed.strip():
                return compressed.strip()

        except Exception as e:
            logger.warning(f"LLM compression failed, falling back to bullet list: {e}")

        # Fallback: plain bullet list
        lines = [f"- {f['content']}" for f in fragments[:20]]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # WebSocket Events
    # ──────────────────────────────────────────────────────────────────────────

    async def _broadcast_personality_update(
        self,
        action: str,
        fragment_id: str,
        content: str,
    ) -> None:
        """Broadcast a personality update event over WebSocket.

        Args:
            action: "approved", "rejected", "deleted", or "inferred".
            fragment_id: UUID of the affected fragment.
            content: Fragment content text.
        """
        try:
            from src.api.websocket.manager import WSMessage, ws_manager

            message = WSMessage(
                type="personality_update",
                data={
                    "action": action,
                    "fragment_id": fragment_id,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            await ws_manager.broadcast(message, channel="personality")
        except Exception as e:
            logger.warning(f"Failed to broadcast personality update: {e}")
