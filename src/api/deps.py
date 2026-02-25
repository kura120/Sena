# src/api/deps.py
"""API Dependencies - Dependency injection for FastAPI routes."""

import time
from typing import AsyncGenerator, Optional

from src.api.websocket.manager import WebSocketManager, ws_manager
from src.core.constants import ProcessingStage
from src.core.sena import Sena
from src.core.telemetry import TelemetryCollector
from src.core.telemetry import get_telemetry as _get_telemetry
from src.database.connection import DatabaseManager
from src.database.connection import get_db as _get_db
from src.database.repositories.extension_repo import ExtensionRepository
from src.database.repositories.memory_repo import MemoryRepository
from src.memory.manager import MemoryManager
from src.utils.logger import logger


async def _ws_stage_callback(stage: ProcessingStage, details: str = "") -> None:
    """Bridge Sena processing stages to WebSocket broadcast."""
    stage_str = stage.value if isinstance(stage, ProcessingStage) else str(stage)
    await ws_manager.broadcast_processing_update(stage_str, details)


# Global Sena instance
_sena_instance: Optional[Sena] = None

# Cooldown between failed init attempts — prevents rapid-fire re-init loop
# when Ollama is unavailable (e.g. still starting up).
_last_init_attempt: float = 0.0
_INIT_COOLDOWN_SECONDS: float = 15.0


async def get_sena() -> Sena:
    """
    Get the global Sena instance.

    On success: returns the initialized instance (cached).
    On failure: resets the instance, records the attempt timestamp,
    and raises. Subsequent callers within the cooldown window receive
    an immediate error instead of triggering a full re-init cycle —
    this prevents log-spam loops when Ollama is not yet ready.
    """
    global _sena_instance, _last_init_attempt

    # Fast path — already initialized
    if _sena_instance is not None and _sena_instance.is_initialized:
        return _sena_instance

    # Cooldown guard — don't hammer re-init while Ollama is starting
    now = time.monotonic()
    if _sena_instance is None and (now - _last_init_attempt) < _INIT_COOLDOWN_SECONDS:
        remaining = _INIT_COOLDOWN_SECONDS - (now - _last_init_attempt)
        raise RuntimeError(
            f"Sena initialization is in cooldown ({remaining:.0f}s remaining). "
            "Previous attempt failed — waiting for Ollama to become ready."
        )

    _last_init_attempt = now
    logger.info("Initializing Sena instance for API...")
    _sena_instance = None  # clean slate so a partial object is never reused
    try:
        _sena_instance = Sena()
        await _sena_instance.initialize()
        _sena_instance.set_stage_callback(_ws_stage_callback)
        logger.info("Sena stage callback wired to WebSocket manager.")
        logger.info(f"Sena instance initialized successfully. Is initialized: {_sena_instance.is_initialized}")
        # Reset cooldown timer on success so a future restart gets a clean slate
        _last_init_attempt = 0.0
    except Exception as e:
        _sena_instance = None  # reset so the next attempt (after cooldown) can retry
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
