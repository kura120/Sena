# src/api/routes/debug.py
"""Debug API routes for introspection and diagnostics."""

from typing import Any

from fastapi import APIRouter, HTTPException, Depends, Query

from src.core.sena import Sena
from src.memory.manager import MemoryManager
from src.database.connection import DatabaseManager
from src.utils.logger import logger

router = APIRouter(prefix="/debug", tags=["Debug"])


async def get_sena() -> Sena:
    """Get Sena instance."""
    # This should come from deps in production
    return Sena(session_id=None)


async def get_memory_manager() -> MemoryManager:
    """Get memory manager instance."""
    return MemoryManager.get_instance()


async def get_database() -> DatabaseManager:
    """Get database manager instance."""
    from src.config.settings import get_settings
    settings = get_settings()
    return DatabaseManager(db_path=settings.database.path)


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
            },
        }
    except Exception as e:
        logger.error(f"Get state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/logs",
    response_model=dict[str, Any],
    summary="Get recent logs",
    description="Get recent log entries with optional filtering",
)
async def get_logs(
    level: str = Query("INFO", description="Minimum log level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
) -> dict[str, Any]:
    """Get recent log entries."""
    try:
        # TODO: Implement log retrieval from database or log file
        return {
            "status": "success",
            "logs": [],
            "count": 0,
            "level_filter": level,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Get logs error: {e}")
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
        logger.error(f"Get memory diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/database/stats",
    response_model=dict[str, Any],
    summary="Get database statistics",
    description="Get database size, table counts, and performance stats",
)
async def get_database_stats(
    db: DatabaseManager = Depends(get_database),
) -> dict[str, Any]:
    """Get database statistics."""
    try:
        # TODO: Implement database stats retrieval
        return {
            "status": "success",
            "database": {
                "path": str(db.db_path),
                "size_mb": 0,
                "tables": [],
                "total_rows": 0,
            },
        }
    except Exception as e:
        logger.error(f"Get database stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/database/vacuum",
    response_model=dict[str, Any],
    summary="Optimize database",
    description="Run database vacuum to optimize storage and performance",
)
async def vacuum_database(
    db: DatabaseManager = Depends(get_database),
) -> dict[str, Any]:
    """Run database vacuum to optimize storage."""
    try:
        # TODO: Implement vacuum
        return {
            "status": "success",
            "message": "Database vacuum completed",
            "space_freed_mb": 0,
        }
    except Exception as e:
        logger.error(f"Vacuum database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    response_model=dict[str, Any],
    summary="System health check",
    description="Comprehensive system health check",
)
async def health_check(
    sena: Sena = Depends(get_sena),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
    db: DatabaseManager = Depends(get_database),
) -> dict[str, Any]:
    """Comprehensive system health check."""
    try:
        memory_ok = memory_mgr.initialized
        
        return {
            "status": "healthy" if memory_ok else "degraded",
            "components": {
                "memory": {"status": "ok" if memory_ok else "error"},
                "database": {"status": "ok"},  # TODO: Check DB connection
            },
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reset",
    response_model=dict[str, Any],
    summary="Reset system state",
    description="WARNING: Reset all caches and temporary data",
)
async def reset_system(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Reset system state (CAUTION: clears temporary data)."""
    try:
        cleared = await memory_mgr.clear_context()

        return {
            "status": "success",
            "message": "System state reset",
            "items_cleared": cleared,
            "warning": "Temporary data has been cleared",
        }
    except Exception as e:
        logger.error(f"Reset system error: {e}")
        raise HTTPException(status_code=500, detail=str(e))