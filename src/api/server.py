# src/api/server.py
"""
FastAPI Server for Sena

Provides REST API and WebSocket endpoints for:
- Chat interactions
- Memory management
- Extension management
- Telemetry and debugging
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.deps import get_sena, shutdown_sena
from src.api.models.responses import HealthResponse
from src.api.routes import (
    chat_router,
    debug_router,
    extensions_router,
    logs_router,
    memory_router,
    personality_router,
    processing_router,
    settings_router,
    telemetry_router,
)
from src.api.websocket.manager import ws_manager
from src.config.settings import get_app_data_dir, get_settings
from src.core.exceptions import SenaException
from src.core.runtime import RUNTIME_ID, get_runtime_info
from src.extensions import get_extension_manager
from src.memory.manager import MemoryManager
from src.utils.logger import logger, setup_logger

settings = get_settings()


def llm_settings_complete() -> bool:
    try:
        current_settings = get_settings()
        provider = current_settings.llm.provider
        models = current_settings.llm.models
        fast = models.get("fast")
        critical = models.get("critical")
        code = models.get("code")
        return bool(provider and fast and fast.name and critical and critical.name and code and code.name)
    except Exception:
        return False


_start_time = datetime.now()

# Production-aware paths: dev → project root, prod → %APPDATA%\Sena
LOG_DIR = get_app_data_dir() / "data" / "logs"
SESSION_DIR = LOG_DIR / "sessions"
LOG_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

setup_logger(
    level=os.getenv("SENA_LOG_LEVEL", "INFO"),
    log_file=str(LOG_DIR / "sena.log"),
    session_dir=str(SESSION_DIR),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting Sena API server...")
    logger.info(f"Runtime ID: {RUNTIME_ID}")
    logger.info("=" * 60)

    # Register sena.local in the OS hosts file (non-fatal if it fails)
    try:
        from src.core.local_domain import setup_sena_local

        local_ok = await setup_sena_local()
        if local_ok:
            logger.info("sena.local is configured — accessible at http://sena.local")
        else:
            logger.info("sena.local not configured — using http://127.0.0.1:8000")
    except Exception as _local_err:
        logger.warning(f"local_domain setup failed (non-fatal): {_local_err}")

    # Initialize Sena (only when LLM settings are complete)
    try:
        if llm_settings_complete():
            sena = await get_sena()
            logger.info("Sena initialized for API server")
        else:
            logger.info("Skipping Sena initialization: LLM settings incomplete")
    except HTTPException as e:
        # get_sena() raises HTTPException(503) on init failure — extract the
        # human-readable message from the detail dict instead of logging the
        # raw "503: {'error': ..., 'message': ...}" repr.
        detail = e.detail
        msg = detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
        logger.error(f"Failed to initialize Sena: {msg}")
    except Exception as e:
        logger.error(f"Failed to initialize Sena: {e}", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down Sena API server...")
    await shutdown_sena()
    logger.info("Sena API server shutdown complete")


app = FastAPI(
    title="Sena API",
    description="Self-Evolving AI Assistant API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS is intentionally disabled by default.
# Sena binds to 127.0.0.1 only and is a local desktop app — same-origin
# enforcement provides no security benefit here. Enable only if you expose
# the API to a browser-based client on a different origin.
_cors = settings.api.cors
if _cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests and responses."""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"

    # Log request
    logger.info(f">>> REQUEST [{request_id}] {request.method} {request.url.path}")
    if request.query_params:
        logger.debug(f"    Query params: {dict(request.query_params)}")

    # Process request
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        # Log response
        logger.info(f"<<< RESPONSE [{request_id}] {response.status_code} ({process_time:.2f}ms)")

        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Runtime-ID"] = RUNTIME_ID

        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"<<< ERROR [{request_id}] {type(e).__name__}: {e} ({process_time:.2f}ms)", exc_info=True)
        raise


# Include routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(personality_router, prefix="/api/v1")
app.include_router(extensions_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(processing_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")

# Serve React static files — path differs between dev and PyInstaller bundle
if getattr(sys, "frozen", False):
    # PyInstaller unpacks data files next to the executable in sys._MEIPASS
    react_build_path = str(Path(getattr(sys, "_MEIPASS", "")) / "ui" / "behind-the-sena" / "dist")
else:
    react_build_path = str(Path(__file__).parent / "../ui/behind-the-sena/dist")

if os.path.exists(react_build_path):
    app.mount("/static", StaticFiles(directory=react_build_path, html=True), name="static")
else:
    logger.warning(f"React build directory not found at {react_build_path}. Static files won't be served.")


@app.get("/", tags=["Root"], include_in_schema=False, response_model=None)
async def serve_frontend():
    """Serve the React frontend."""
    if getattr(sys, "frozen", False):
        index_path = str(Path(getattr(sys, "_MEIPASS", "")) / "ui" / "behind-the-sena" / "dist" / "index.html")
    else:
        index_path = str(Path(__file__).parent / "../ui/behind-the-sena/dist/index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback if React build doesn't exist (dev without a build)
    return JSONResponse({"name": "Sena API", "version": "1.0.0", "docs": "/docs"})


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> Any:
    """Health check endpoint."""
    status = "healthy"
    sena = None
    try:
        llm_health = {}
        if llm_settings_complete():
            sena = await get_sena()
            llm_health = await sena._llm_manager.health_check() if sena._llm_manager else {}
        # Memory manager status
        try:
            mem_mgr = MemoryManager.get_instance()
            memory_status = {
                "initialized": mem_mgr.initialized,
                "provider": settings.memory.provider,
            }
        except Exception:
            memory_status = {"error": "memory manager unavailable"}

        # Extensions status
        try:
            ext_mgr = get_extension_manager()
            extensions = ext_mgr.list()
            extensions_status = {"count": len(extensions)}
        except Exception:
            extensions_status = {"error": "extensions unavailable"}
    except Exception:
        llm_health = {"error": "Failed to check LLM health"}
        memory_status = {"error": "Failed to check memory"}
        extensions_status = {"error": "Failed to check extensions"}

    response = {
        "status": status,
        "version": "1.0.0",
        "runtime": get_runtime_info(),
        "components": {
            "sena": {
                "initialized": sena.is_initialized if sena else False,
                "session_id": sena.session_id if sena else None,
            },
            "llm": llm_health,
            "memory": memory_status,
            "extensions": extensions_status,
            "websocket": {
                "connections": ws_manager.connection_count,
            },
        },
    }

    return HealthResponse(**response)


@app.get("/stats", tags=["Stats"])
async def stats() -> dict[str, Any]:
    """Get server statistics."""
    uptime = (datetime.now() - _start_time).total_seconds()

    try:
        sena = await get_sena()
        sena_stats = sena.get_stats()
    except Exception:
        sena_stats = {}

    return {
        **get_runtime_info(),
        "websocket_connections": ws_manager.connection_count,
        "sena": sena_stats,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time updates."""
    client_id = await ws_manager.connect(websocket)

    if client_id is None:
        return

    try:
        while True:
            # Receive and handle messages
            data = await websocket.receive_text()
            await ws_manager.handle_client_message(client_id, data)

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
    except RuntimeError as e:
        message = str(e)
        if "WebSocket is not connected" in message or "accept" in message:
            await ws_manager.disconnect(client_id)
            return
        logger.error(f"WebSocket error for {client_id}: {e}")
        await ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await ws_manager.disconnect(client_id)


@app.exception_handler(SenaException)
async def sena_exception_handler(request: Request, exc: SenaException) -> JSONResponse:
    """
    Convert known SenaException subclasses to appropriate HTTP responses.

    Recoverable errors (LLMConnectionError, etc.) → 503 Service Unavailable.
    Non-recoverable domain errors → 500 Internal Server Error.
    Uses WARNING level for recoverable/startup errors so they don't pollute
    the Logs tab as false 'UNHANDLED EXCEPTION' entries.
    """
    status_code = 503 if exc.recoverable else 500
    if exc.recoverable:
        logger.warning(f"[{exc.code}] {exc.message} ({request.method} {request.url.path})")
    else:
        logger.error(
            f"[{exc.code}] {exc.message} ({request.method} {request.url.path})",
            exc_info=True,
        )
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for truly unexpected exceptions.

    Logs as a single ERROR entry (with traceback via exc_info) instead of the
    previous 5-line format that produced 5 separate rows in the Logs tab.
    HTTPException subclasses are re-delegated to FastAPI's built-in handler so
    they are never mis-classified as unhandled errors.
    """
    # HTTPExceptions (including our 503s from deps.py) should never reach here,
    # but guard defensively in case a middleware raises one.
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    logger.error(
        f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc),
            "type": type(exc).__name__,
        },
    )


async def start_server() -> None:
    """Start the API server."""
    import uvicorn

    config = uvicorn.Config(
        app=app,
        host=settings.api.host,
        port=settings.api.port,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(start_server())
