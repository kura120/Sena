# src/api/routes/debug.py
"""Debug API routes for introspection and diagnostics."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db, get_memory_manager, get_sena
from src.core.sena import Sena
from src.database.connection import DatabaseManager
from src.memory.manager import MemoryManager
from src.utils.logger import logger

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get(
    "/state",
    response_model=dict[str, Any],
    summary="Get current processing state",
    description="Get current Sena processing state and statistics",
)
async def get_state(
    sena: Sena = Depends(get_sena),
) -> dict[str, Any]:
    """Get current Sena processing state."""
    try:
        return {
            "status": "success",
            "sena": {
                "session_id": sena.session_id,
                "initialized": sena.is_initialized,
            },
        }
    except Exception as e:
        logger.error(f"Get state error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/memory",
    response_model=dict[str, Any],
    summary="Get memory diagnostics",
    description="Get detailed memory system diagnostics",
)
async def get_memory_diagnostics(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Get memory system diagnostics."""
    try:
        stats = await memory_mgr.get_memory_stats()
        retrieval_stats = await memory_mgr.get_retrieval_stats()

        return {
            "status": "success",
            "memory": stats,
            "retrieval": retrieval_stats,
        }
    except Exception as e:
        logger.error(f"Get memory diagnostics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/database/stats",
    response_model=dict[str, Any],
    summary="Get database statistics",
    description="Get database path and basic connection info",
)
async def get_database_stats(
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    """Get database statistics."""
    try:
        import os

        db_path = str(db.db_path)
        size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0

        return {
            "status": "success",
            "database": {
                "path": db_path,
                "size_mb": round(size_bytes / 1_048_576, 3),
                "exists": os.path.exists(db_path),
            },
        }
    except Exception as e:
        logger.error(f"Get database stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/database/vacuum",
    response_model=dict[str, Any],
    summary="Optimize database",
    description="Run VACUUM to reclaim unused space and defragment the SQLite file",
)
async def vacuum_database(
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    """Run database VACUUM to optimize storage."""
    try:
        import os

        db_path = str(db.db_path)
        size_before = os.path.getsize(db_path) if os.path.exists(db_path) else 0

        await db.vacuum()

        size_after = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        freed_mb = round((size_before - size_after) / 1_048_576, 3)

        return {
            "status": "success",
            "message": "Database VACUUM completed",
            "space_freed_mb": freed_mb,
        }
    except Exception as e:
        logger.error(f"Vacuum database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    response_model=dict[str, Any],
    summary="System health check",
    description="Comprehensive system health check across all components",
)
async def health_check(
    sena: Sena = Depends(get_sena),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    """Comprehensive system health check."""
    try:
        import os

        memory_ok = memory_mgr.initialized
        sena_ok = sena.is_initialized
        db_path = str(db.db_path)
        db_ok = os.path.exists(db_path)

        overall = "healthy" if (memory_ok and sena_ok and db_ok) else "degraded"

        return {
            "status": overall,
            "components": {
                "sena": {
                    "status": "ok" if sena_ok else "error",
                    "initialized": sena_ok,
                    "session_id": sena.session_id,
                },
                "memory": {
                    "status": "ok" if memory_ok else "error",
                    "initialized": memory_ok,
                },
                "database": {
                    "status": "ok" if db_ok else "error",
                    "path": db_path,
                },
            },
        }
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reset",
    response_model=dict[str, Any],
    summary="Reset system state",
    description="WARNING: Clears short-term memory context and resets caches",
)
async def reset_system(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Reset system state (clears short-term memory context)."""
    try:
        cleared = await memory_mgr.clear_context()

        return {
            "status": "success",
            "message": "System state reset",
            "items_cleared": cleared,
            "warning": "Short-term memory context has been cleared",
        }
    except Exception as e:
        logger.error(f"Reset system error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
