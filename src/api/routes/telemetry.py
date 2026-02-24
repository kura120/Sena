# src/api/routes/telemetry.py
"""
Telemetry API routes for metrics and analytics.

Currently returns real data where available (uptime, WebSocket connections)
and clearly-empty structures where telemetry collection is not yet wired up.
Fake/hardcoded placeholder values have been removed.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_sena
from src.api.websocket.manager import ws_manager
from src.config.settings import get_settings
from src.core.sena import Sena
from src.utils.logger import logger

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get(
    "/metrics",
    response_model=dict[str, Any],
    summary="Get performance metrics",
    description="Get available performance metrics. Returns empty counters until telemetry collection is fully wired.",
)
async def get_metrics(
    hours: int = Query(24, ge=1, le=720, description="Hours of historical data"),
    sena: Sena = Depends(get_sena),
) -> dict[str, Any]:
    """Get performance metrics."""
    try:
        sena_stats = sena.get_stats() if sena.is_initialized else {}

        return {
            "status": "success",
            "time_range": {
                "start": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours,
            },
            "metrics": {
                "requests_total": sena_stats.get("total_requests", 0),
                "requests_today": sena_stats.get("requests_today", 0),
                "avg_response_time_ms": sena_stats.get("avg_response_time_ms", 0.0),
                "errors": sena_stats.get("error_count", 0),
                "successful_requests": sena_stats.get("successful_requests", 0),
                "failed_requests": sena_stats.get("error_count", 0),
                "success_rate": sena_stats.get("success_rate", 0.0),
                "uptime_seconds": sena_stats.get("uptime_seconds", 0.0),
            },
            "websocket": {
                "active_connections": ws_manager.connection_count,
            },
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/errors",
    response_model=dict[str, Any],
    summary="Get error statistics",
    description="Get error statistics. Returns empty structures until error tracking is wired to the database.",
)
async def get_errors(
    hours: int = Query(24, ge=1, le=720),
) -> dict[str, Any]:
    """Get error statistics."""
    try:
        return {
            "status": "success",
            "time_range": {
                "start": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours,
            },
            "errors": {
                "total": 0,
                "by_type": {},
                "by_component": {},
                "recent": [],
            },
        }
    except Exception as e:
        logger.error(f"Errors endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/models",
    response_model=dict[str, Any],
    summary="Get model performance metrics",
    description="Per-model performance stats. Returns empty until model telemetry is wired to the database.",
)
async def get_model_metrics(
    hours: int = Query(24, ge=1, le=720),
) -> dict[str, Any]:
    """Get model performance metrics."""
    try:
        settings = get_settings()
        # Return the configured model slots with zero counters —
        # real data will come once telemetry is persisted to DB.
        model_slots = {
            slot: {
                "name": cfg.name if cfg else None,
                "requests": 0,
                "avg_response_ms": 0.0,
                "errors": 0,
            }
            for slot, cfg in settings.llm.models.items()
        }

        return {
            "status": "success",
            "time_range": {
                "start": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours,
            },
            "models": model_slots,
        }
    except Exception as e:
        logger.error(f"Model metrics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/extensions",
    response_model=dict[str, Any],
    summary="Get extension performance metrics",
    description="Per-extension usage and timing stats. Returns live list with zero counters until telemetry DB is wired.",
)
async def get_extension_metrics(
    hours: int = Query(24, ge=1, le=720),
) -> dict[str, Any]:
    """Get extension performance metrics."""
    try:
        from src.extensions import get_extension_manager

        mgr = get_extension_manager()
        extensions = mgr.list()

        ext_stats = {
            ext.get("name", "unknown"): {
                "enabled": ext.get("enabled", False),
                "requests": 0,
                "avg_execution_ms": 0.0,
                "errors": 0,
            }
            for ext in extensions
            if isinstance(ext, dict)
        }

        return {
            "status": "success",
            "time_range": {
                "start": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours,
            },
            "extensions": ext_stats,
            "total_extensions": len(ext_stats),
        }
    except Exception as e:
        logger.error(f"Extension metrics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/trends",
    response_model=dict[str, Any],
    summary="Get performance trends",
    description="Historical trends. Returns stable/zero values until trend analysis is implemented.",
)
async def get_trends(
    hours: int = Query(168, ge=1, le=720),
) -> dict[str, Any]:
    """Get performance trends."""
    try:
        return {
            "status": "success",
            "time_range": {
                "start": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours,
            },
            "trends": {
                "response_time_ms": {"current": 0.0, "trend": "no_data"},
                "error_rate": {"current": 0.0, "trend": "no_data"},
                "throughput_rps": {"current": 0.0, "trend": "no_data"},
            },
        }
    except Exception as e:
        logger.error(f"Trends error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/system",
    response_model=dict[str, Any],
    summary="Get live system stats",
    description="Returns live data that is always available: uptime, WebSocket connections, settings snapshot.",
)
async def get_system_stats(
    sena: Sena = Depends(get_sena),
) -> dict[str, Any]:
    """Get always-available live system stats."""
    try:
        settings = get_settings()
        sena_stats = sena.get_stats() if sena.is_initialized else {}

        return {
            "status": "success",
            "sena": {
                "initialized": sena.is_initialized,
                "session_id": sena.session_id,
                "uptime_seconds": sena_stats.get("uptime_seconds", 0.0),
            },
            "websocket": {
                "active_connections": ws_manager.connection_count,
                "max_connections": settings.api.websocket.max_connections,
            },
            "llm": {
                "provider": settings.llm.provider,
                "base_url": settings.llm.base_url,
            },
            "telemetry_enabled": settings.telemetry.enabled,
        }
    except Exception as e:
        logger.error(f"System stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
