# src/api/routes/processing.py
"""
Processing pipeline status API routes.

Pipeline state is tracked in a lightweight in-process registry that is updated
by the Sena orchestrator (via WebSocket events or direct calls).  Routes expose
the current state so the frontend can poll or subscribe via WebSocket.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from src.utils.logger import logger

router = APIRouter(prefix="/processing", tags=["Processing"])

# ---------------------------------------------------------------------------
# Pipeline registry
# ---------------------------------------------------------------------------
# Keyed by request_id.  The orchestrator calls `start_pipeline`,
# `update_stage`, and `finish_pipeline` as processing progresses.
# The frontend can poll /processing/status or listen on the WebSocket.
# ---------------------------------------------------------------------------

STAGE_NAMES: list[str] = ["intent", "memory", "extension", "llm", "post"]

PipelineStatus = Literal["idle", "active", "completed", "error"]
StageStatus = Literal["pending", "active", "completed", "error", "skipped"]

_pipelines: dict[str, dict[str, Any]] = {}
_active_request_id: str | None = None


def _empty_stages() -> dict[str, dict[str, Any]]:
    return {name: {"status": "pending", "started_at": None, "duration_ms": None, "detail": ""} for name in STAGE_NAMES}


def start_pipeline(request_id: str | None = None) -> str:
    """
    Register a new pipeline run.  Returns the request_id.
    Called by the Sena orchestrator at the start of each request.
    """
    global _active_request_id
    rid = request_id or f"req_{uuid.uuid4().hex[:8]}"
    _pipelines[rid] = {
        "request_id": rid,
        "status": "active",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "current_stage": STAGE_NAMES[0],
        "stages": _empty_stages(),
        "error": None,
    }
    _active_request_id = rid
    return rid


def update_stage(
    request_id: str,
    stage: str,
    status: StageStatus,
    detail: str = "",
    duration_ms: float | None = None,
) -> None:
    """
    Update a single stage's status inside an active pipeline.
    Called by the Sena orchestrator as each stage completes or errors.
    """
    pipeline = _pipelines.get(request_id)
    if pipeline is None:
        logger.warning(f"update_stage called for unknown request_id={request_id}")
        return
    if stage not in pipeline["stages"]:
        logger.warning(f"update_stage: unknown stage '{stage}' for request_id={request_id}")
        return

    pipeline["stages"][stage].update(
        {
            "status": status,
            "detail": detail,
            "duration_ms": duration_ms,
        }
    )

    if status == "active":
        pipeline["stages"][stage]["started_at"] = datetime.now().isoformat()
        pipeline["current_stage"] = stage
    elif status in ("completed", "error", "skipped"):
        # Advance current_stage pointer to the next pending stage
        try:
            idx = STAGE_NAMES.index(stage)
            for next_stage in STAGE_NAMES[idx + 1 :]:
                if pipeline["stages"][next_stage]["status"] == "pending":
                    pipeline["current_stage"] = next_stage
                    break
        except (ValueError, IndexError):
            pass


def finish_pipeline(request_id: str, error: str | None = None) -> None:
    """Mark a pipeline as completed or errored."""
    pipeline = _pipelines.get(request_id)
    if pipeline is None:
        return
    pipeline["status"] = "error" if error else "completed"
    pipeline["finished_at"] = datetime.now().isoformat()
    pipeline["error"] = error

    # Keep only the last 50 pipelines in memory
    while len(_pipelines) > 50:
        oldest = next(iter(_pipelines))
        del _pipelines[oldest]


def get_active_pipeline() -> dict[str, Any] | None:
    """Return the most recently started pipeline, or None if no runs yet."""
    if _active_request_id and _active_request_id in _pipelines:
        return _pipelines[_active_request_id]
    if _pipelines:
        return next(reversed(_pipelines.values()))
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=dict[str, Any],
    summary="Get current pipeline status",
    description="Returns the state of the most recently active processing pipeline.",
)
async def get_processing_status() -> dict[str, Any]:
    """
    Return the latest pipeline run.  If no run has started yet the response
    will indicate an idle state — never fake/hardcoded data.
    """
    try:
        pipeline = get_active_pipeline()

        if pipeline is None:
            return {
                "status": "idle",
                "request_id": None,
                "started_at": None,
                "current_stage": None,
                "stages": {},
                "message": "No pipeline run recorded yet",
            }

        return {
            "status": pipeline["status"],
            "request_id": pipeline["request_id"],
            "started_at": pipeline["started_at"],
            "finished_at": pipeline.get("finished_at"),
            "current_stage": pipeline["current_stage"],
            "stages": pipeline["stages"],
            "error": pipeline.get("error"),
        }
    except Exception as e:
        logger.error(f"Get processing status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stages",
    response_model=dict[str, Any],
    summary="Get pipeline stage definitions",
    description="Returns the ordered list of processing stages.",
)
async def get_pipeline_stages() -> dict[str, Any]:
    """Return metadata about each pipeline stage."""
    try:
        stage_descriptions = {
            "intent": "Classify user intent and select routing strategy",
            "memory": "Retrieve relevant long-term memories",
            "extension": "Execute any matching extensions",
            "llm": "Generate response via LLM",
            "post": "Post-process, store learnings, emit events",
        }

        pipeline = get_active_pipeline()
        current_statuses = (
            {name: pipeline["stages"][name]["status"] for name in STAGE_NAMES}
            if pipeline
            else {name: "pending" for name in STAGE_NAMES}
        )

        return {
            "stages": STAGE_NAMES,
            "stage_count": len(STAGE_NAMES),
            "details": {
                name: {
                    "description": stage_descriptions.get(name, ""),
                    "status": current_statuses.get(name, "pending"),
                }
                for name in STAGE_NAMES
            },
        }
    except Exception as e:
        logger.error(f"Get pipeline stages error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=dict[str, Any],
    summary="Get recent pipeline runs",
    description="Returns the last N pipeline runs (up to 50 kept in memory).",
)
async def get_pipeline_history(limit: int = 10) -> dict[str, Any]:
    """Return recent pipeline runs for diagnostics."""
    try:
        limit = max(1, min(limit, 50))
        recent = list(reversed(list(_pipelines.values())))[:limit]

        return {
            "runs": [
                {
                    "request_id": p["request_id"],
                    "status": p["status"],
                    "started_at": p["started_at"],
                    "finished_at": p.get("finished_at"),
                    "current_stage": p["current_stage"],
                    "error": p.get("error"),
                }
                for p in recent
            ],
            "total_recorded": len(_pipelines),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Get pipeline history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
