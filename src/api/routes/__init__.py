# src/api/routes/__init__.py
"""API Routes."""

from src.api.routes.chat import router as chat_router
from src.api.routes.debug import router as debug_router
from src.api.routes.extensions import router as extensions_router
from src.api.routes.logs import router as logs_router
from src.api.routes.memory import router as memory_router
from src.api.routes.personality import router as personality_router
from src.api.routes.processing import router as processing_router
from src.api.routes.settings import router as settings_router
from src.api.routes.telemetry import router as telemetry_router

__all__ = [
    "chat_router",
    "memory_router",
    "personality_router",
    "extensions_router",
    "debug_router",
    "telemetry_router",
    "processing_router",
    "logs_router",
    "settings_router",
]
