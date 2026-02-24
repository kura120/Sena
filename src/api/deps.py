# src/api/deps.py
"""API Dependencies - Dependency injection for FastAPI routes."""

from typing import AsyncGenerator, Optional

from src.api.websocket.manager import WebSocketManager, ws_manager
from src.core.sena import Sena
from src.core.telemetry import TelemetryCollector
from src.core.telemetry import get_telemetry as _get_telemetry
from src.database.connection import DatabaseManager
from src.database.connection import get_db as _get_db
from src.database.repositories.extension_repo import ExtensionRepository
from src.database.repositories.memory_repo import MemoryRepository
from src.memory.manager import MemoryManager
from src.utils.logger import logger

# Global Sena instance
_sena_instance: Optional[Sena] = None


async def get_sena() -> Sena:
    """Get the global Sena instance."""
    global _sena_instance

    if _sena_instance is None:
        logger.info("Initializing Sena instance for API...")
        try:
            _sena_instance = Sena()
            await _sena_instance.initialize()
            logger.info(f"Sena instance initialized successfully. Is initialized: {_sena_instance.is_initialized}")
        except Exception as e:
            logger.error(f"Failed to initialize Sena instance: {type(e).__name__}: {e}", exc_info=True)
            raise

    return _sena_instance


async def get_memory_manager() -> MemoryManager:
    """Get the canonical MemoryManager instance, initializing it if needed."""
    mgr = MemoryManager.get_instance()
    if not mgr.initialized:
        await mgr.initialize()
    return mgr


async def get_db() -> DatabaseManager:
    """Get the database manager."""
    return await _get_db()


async def get_memory_repo() -> MemoryRepository:
    """Get the memory repository."""
    db = await get_db()
    return MemoryRepository(db)


async def get_extension_repo() -> ExtensionRepository:
    """Get the extension repository."""
    db = await get_db()
    return ExtensionRepository(db)


async def get_telemetry() -> TelemetryCollector:
    """Get the telemetry collector."""
    return await _get_telemetry()


def get_ws_manager() -> WebSocketManager:
    """Get the WebSocket manager."""
    return ws_manager


async def shutdown_sena() -> None:
    """Shutdown the global Sena instance."""
    global _sena_instance

    if _sena_instance:
        await _sena_instance.shutdown()
        _sena_instance = None
