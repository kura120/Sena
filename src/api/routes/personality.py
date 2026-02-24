# src/api/routes/personality.py
"""
Personality API Routes

Provides REST endpoints for managing Sena's personality system:
- GET  /api/v1/personality              - List all approved fragments
- POST /api/v1/personality              - Add an explicit personality fragment
- GET  /api/v1/personality/pending      - List pending (awaiting approval) fragments
- GET  /api/v1/personality/stats        - Aggregate stats
- GET  /api/v1/personality/preview      - Preview the composed personality block
- POST /api/v1/personality/infer        - Trigger manual inference from recent conversation
- GET  /api/v1/personality/{id}         - Get a single fragment
- PUT  /api/v1/personality/{id}         - Edit a fragment's content
- DELETE /api/v1/personality/{id}       - Delete a fragment
- POST /api/v1/personality/{id}/approve - Approve a pending fragment
- POST /api/v1/personality/{id}/reject  - Reject a pending fragment
- GET  /api/v1/personality/audit        - Audit log (all fragments)
- GET  /api/v1/personality/{id}/audit   - Audit log for a specific fragment
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.utils.logger import logger

router = APIRouter(prefix="/personality", tags=["Personality"])


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────


class CreateFragmentRequest(BaseModel):
    """Request body for creating an explicit personality fragment."""

    content: str = Field(..., min_length=1, max_length=2000, description="The personality fact text.")
    category: Optional[str] = Field(
        None,
        description="Category label (preference, trait, habit, fact, goal, dislike, relationship, work, health, hobby).",
    )
    source: Optional[str] = Field("user_input", description="Where this fragment came from.")
    metadata: Optional[dict[str, Any]] = Field(None, description="Optional arbitrary metadata.")


class EditFragmentRequest(BaseModel):
    """Request body for editing a fragment's content."""

    content: str = Field(..., min_length=1, max_length=2000, description="Updated personality fact text.")
    approve: bool = Field(
        True,
        description="If True, immediately approve the fragment after editing. Default True.",
    )
    reason: Optional[str] = Field(None, description="Optional reason for the edit.")


class ApproveRejectRequest(BaseModel):
    """Request body for approve/reject actions."""

    reason: Optional[str] = Field(None, description="Optional human-readable reason for this decision.")


class InferRequest(BaseModel):
    """Request body for triggering manual inference."""

    conversation: Optional[str] = Field(
        None,
        description=("Conversation text to analyze. If omitted, the most recent session conversation is used."),
    )
    source: Optional[str] = Field("manual_trigger", description="Label for the inference source.")


# ──────────────────────────────────────────────────────────────────────────────
# Dependency helper
# ──────────────────────────────────────────────────────────────────────────────


async def _get_manager():
    """Get (and lazily initialize) the PersonalityManager singleton."""
    from src.memory.personality import PersonalityManager

    mgr = PersonalityManager.get_instance()
    if not mgr._initialized:
        ok = await mgr.initialize()
        if not ok:
            raise HTTPException(status_code=503, detail="PersonalityManager not available")
    return mgr


# ──────────────────────────────────────────────────────────────────────────────
# List / Stats / Preview
# ──────────────────────────────────────────────────────────────────────────────


@router.get("", response_model=dict)
async def list_fragments(
    status: Optional[str] = Query(None, description="Filter by status: approved | pending | rejected"),
    fragment_type: Optional[str] = Query(None, description="Filter by type: explicit | inferred"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """List personality fragments with optional filters.

    Returns all fragments (default: no filter) or filtered by status/type.
    """
    try:
        mgr = await _get_manager()
        fragments = await mgr.get_all_fragments(
            status=status,
            fragment_type=fragment_type,
            limit=limit,
        )
        return {
            "status": "success",
            "data": fragments,
            "total": len(fragments),
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing personality fragments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=dict)
async def list_pending() -> dict:
    """Return all fragments awaiting user approval.

    These are inferred fragments that have not yet been approved or rejected.
    """
    try:
        mgr = await _get_manager()
        pending = await mgr.get_pending_fragments()
        return {
            "status": "success",
            "data": pending,
            "total": len(pending),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing pending personality fragments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict)
async def get_stats() -> dict:
    """Return aggregate statistics about personality fragments."""
    try:
        mgr = await _get_manager()
        stats = await mgr.get_stats()
        return {
            "status": "success",
            "data": stats,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching personality stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview", response_model=dict)
async def preview_personality_block() -> dict:
    """Preview the composed personality block as it would appear in the system prompt.

    Always returns a freshly built block (bypasses cache).
    """
    try:
        mgr = await _get_manager()
        block = await mgr.get_preview_block()
        return {
            "status": "success",
            "data": {"block": block},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing personality block: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit", response_model=dict)
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Return the global personality audit log (newest first)."""
    try:
        mgr = await _get_manager()
        entries = await mgr.get_audit_log(limit=limit)
        return {
            "status": "success",
            "data": entries,
            "total": len(entries),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching personality audit log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Create (explicit fragment)
# ──────────────────────────────────────────────────────────────────────────────


@router.post("", response_model=dict, status_code=201)
async def create_fragment(body: CreateFragmentRequest) -> dict:
    """Store a user-explicitly-stated personality fact.

    Explicit fragments are immediately approved and added to the personality block.
    """
    try:
        mgr = await _get_manager()
        fragment = await mgr.store_explicit(
            content=body.content,
            category=body.category,
            source=body.source or "user_input",
            metadata=body.metadata,
        )

        if not fragment:
            raise HTTPException(status_code=500, detail="Failed to create personality fragment")

        return {
            "status": "success",
            "data": fragment,
            "message": "Personality fragment stored and approved",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating personality fragment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Inference trigger
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/infer", response_model=dict)
async def trigger_inference(body: InferRequest) -> dict:
    """Manually trigger personality inference from a conversation.

    If no conversation text is provided, uses the most recent session context.
    Returns a list of newly created fragments (may be pending or auto-approved).
    """
    try:
        mgr = await _get_manager()

        conversation_text = body.conversation

        # Fall back to recent memory context if no conversation provided
        if not conversation_text:
            try:
                from src.memory.manager import MemoryManager

                mem_mgr = MemoryManager.get_instance()
                conversation_text = await mem_mgr.get_conversation_context()
            except Exception as e:
                logger.warning(f"Could not retrieve conversation context for inference: {e}")

        if not conversation_text or not conversation_text.strip():
            return {
                "status": "success",
                "data": [],
                "message": "No conversation text available for inference",
            }

        fragments = await mgr.infer_from_conversation(
            conversation=conversation_text,
            source=body.source or "manual_trigger",
        )

        pending_count = sum(1 for f in fragments if f.get("status") == "pending")
        approved_count = sum(1 for f in fragments if f.get("status") == "approved")

        return {
            "status": "success",
            "data": fragments,
            "total": len(fragments),
            "pending": pending_count,
            "auto_approved": approved_count,
            "message": (
                f"Inference complete: {len(fragments)} fragment(s) extracted "
                f"({pending_count} pending approval, {approved_count} auto-approved)"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering personality inference: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Single fragment operations
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/{fragment_id}", response_model=dict)
async def get_fragment(fragment_id: str) -> dict:
    """Fetch a single personality fragment by its UUID."""
    try:
        mgr = await _get_manager()

        if not mgr._repo:
            raise HTTPException(status_code=503, detail="Personality repository not available")

        fragment = await mgr._repo.get_by_id(fragment_id)
        if not fragment:
            raise HTTPException(status_code=404, detail=f"Fragment '{fragment_id}' not found")

        return {
            "status": "success",
            "data": fragment,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching personality fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{fragment_id}", response_model=dict)
async def edit_fragment(fragment_id: str, body: EditFragmentRequest) -> dict:
    """Edit a fragment's content.

    If approve=True (default), the fragment is also approved immediately after editing.
    """
    try:
        mgr = await _get_manager()

        if body.approve:
            success = await mgr.edit_and_approve(
                fragment_id=fragment_id,
                new_content=body.content,
                reason=body.reason,
            )
        else:
            # Edit only, leave status unchanged
            if not mgr._repo:
                raise HTTPException(status_code=503, detail="Personality repository not available")
            success = await mgr._repo.update_fragment(fragment_id, content=body.content)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Fragment '{fragment_id}' not found or update failed",
            )

        return {
            "status": "success",
            "message": f"Fragment {'edited and approved' if body.approve else 'edited'}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing personality fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{fragment_id}", response_model=dict)
async def delete_fragment(fragment_id: str) -> dict:
    """Permanently delete a personality fragment."""
    try:
        mgr = await _get_manager()
        success = await mgr.delete_fragment(fragment_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Fragment '{fragment_id}' not found")

        return {
            "status": "success",
            "message": f"Fragment '{fragment_id}' deleted",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting personality fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fragment_id}/approve", response_model=dict)
async def approve_fragment(fragment_id: str, body: Optional[ApproveRejectRequest] = None) -> dict:
    """Approve a pending personality fragment.

    Once approved, the fragment will be included in Sena's system prompt personality block.
    """
    try:
        mgr = await _get_manager()
        success = await mgr.approve_fragment(fragment_id=fragment_id, reason=body.reason if body else None)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Fragment '{fragment_id}' not found or already processed",
            )

        return {
            "status": "success",
            "message": f"Fragment '{fragment_id}' approved and added to personality",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving personality fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fragment_id}/reject", response_model=dict)
async def reject_fragment(fragment_id: str, body: Optional[ApproveRejectRequest] = None) -> dict:
    """Reject a pending personality fragment.

    Rejected fragments are kept in the database for audit purposes but will not
    be included in the personality block.
    """
    try:
        mgr = await _get_manager()
        success = await mgr.reject_fragment(fragment_id=fragment_id, reason=body.reason if body else None)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Fragment '{fragment_id}' not found or already processed",
            )

        return {
            "status": "success",
            "message": f"Fragment '{fragment_id}' rejected",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting personality fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fragment_id}/audit", response_model=dict)
async def get_fragment_audit_log(
    fragment_id: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Return the audit log for a specific personality fragment."""
    try:
        mgr = await _get_manager()
        entries = await mgr.get_audit_log(fragment_id=fragment_id, limit=limit)
        return {
            "status": "success",
            "data": entries,
            "total": len(entries),
            "fragment_id": fragment_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching audit log for fragment {fragment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
