"""Processing pipeline status API endpoints."""

from typing import Literal
from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter(prefix="/processing", tags=["Processing"])

# In-memory pipeline state (would be replaced with real pipeline tracking)
_pipeline_state = {
    "request_id": "req_1247_post",
    "started_at": datetime.now().isoformat(),
    "stages": {
        "intent": {
            "status": "completed",
            "duration": 0.3,
            "data": {
                "stage": "intent",
                "model": "gemma2:2b",
                "context_length": 2048,
                "extensions": ["web_search"],
                "memory_retrieved": 3,
            },
        },
        "memory": {
            "status": "active",
            "duration": None,
            "data": {
                "stage": "memory",
                "model": "gemma2:2b",
                "context_length": 2048,
                "extensions": ["web_search"],
                "memory_retrieved": 3,
            },
        },
        "extension": {
            "status": "pending",
            "duration": None,
            "data": {
                "stage": "extension",
                "model": "gemma2:2b",
                "context_length": 2048,
                "extensions": ["web_search"],
                "memory_retrieved": 3,
            },
        },
        "llm": {
            "status": "pending",
            "duration": None,
            "data": {
                "stage": "llm",
                "model": "gemma2:2b",
                "context_length": 2048,
                "extensions": ["web_search"],
                "memory_retrieved": 3,
            },
        },
        "post": {
            "status": "pending",
            "duration": None,
            "data": {
                "stage": "post",
                "model": "gemma2:2b",
                "context_length": 2048,
                "extensions": ["web_search"],
                "memory_retrieved": 3,
            },
        },
    },
    "current_stage": "memory",
    "currently_processing": "Post-processing response...",
}


@router.get(
    "/status",
    response_model=dict,
    summary="Get processing pipeline status",
    description="Get real-time status of the processing pipeline.",
)
async def get_processing_status():
    """
    Get the current status of the processing pipeline.
    
    Returns information about each stage, timing, and current progress.
    """
    return {
        "request_id": _pipeline_state["request_id"],
        "started_at": _pipeline_state["started_at"],
        "stages": _pipeline_state["stages"],
        "current_stage": _pipeline_state["current_stage"],
        "currently_processing": _pipeline_state["currently_processing"],
    }


@router.get(
    "/stages",
    response_model=dict,
    summary="Get pipeline stages",
    description="Get all available processing stages.",
)
async def get_pipeline_stages():
    """Get information about all pipeline stages."""
    stages = list(_pipeline_state["stages"].keys())
    return {
        "stages": stages,
        "stage_count": len(stages),
        "details": {
            name: {
                "status": stage["status"],
                "duration": stage["duration"],
            }
            for name, stage in _pipeline_state["stages"].items()
        },
    }
