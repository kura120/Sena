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
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from src.config.settings import get_settings
from src.api.routes import (
    chat_router,
    memory_router,
    extensions_router,
    debug_router,
    telemetry_router,
    processing_router,
    logs_router,
)
from src.api.websocket.manager import ws_manager
from src.api.deps import get_sena, shutdown_sena
from src.api.models.responses import HealthResponse
from src.utils.logger import logger, setup_logger
from src.memory.manager import MemoryManager
from src.extensions import get_extension_manager


settings = get_settings()
_start_time = datetime.now()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "data" / "logs"
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
    logger.info("Starting Sena API server...")
    
    # Initialize Sena
    try:
        sena = await get_sena()
        logger.info("Sena initialized for API server")
    except Exception as e:
        logger.error(f"Failed to initialize Sena: {e}")
    
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
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
        
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        logger.error(f"<<< ERROR [{request_id}] {type(e).__name__}: {e} ({process_time:.2f}ms)", exc_info=True)
        raise


# Include routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(extensions_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(processing_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")

# Serve React static files
react_build_path = os.path.join(os.path.dirname(__file__), "../ui/behind-the-sena/dist")
if os.path.exists(react_build_path):
    app.mount("/static", StaticFiles(directory=react_build_path, html=True), name="static")
else:
    logger.warning(f"React build directory not found at {react_build_path}. Static files won't be served.")


@app.get("/", tags=["Root"], include_in_schema=False, response_model=None)
async def serve_frontend():
    """Serve the React frontend."""
    react_build_path = os.path.join(os.path.dirname(__file__), "../ui/behind-the-sena/dist/index.html")
    if os.path.exists(react_build_path):
        return FileResponse(react_build_path)
    # Fallback if React build doesn't exist
    return JSONResponse({"name": "Sena API", "version": "1.0.0", "docs": "/docs"})


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> Any:
    """Health check endpoint."""
    status = "healthy"
    try:
        sena = await get_sena()
        llm_health = await sena._llm_manager.health_check() if sena._llm_manager else {}
        # Memory manager status
        try:
            mem_mgr = MemoryManager.get_instance()
            mem0_connected = await mem_mgr.mem0_client.check_connection()
            memory_status = {
                "initialized": mem_mgr.initialized,
                "provider": settings.memory.provider,
                "mem0_connected": mem0_connected,
            }
            if settings.memory.provider == "mem0" and not mem0_connected:
                status = "degraded"
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
        "components": {
            "sena": {"initialized": sena.is_initialized if sena else False, "session_id": sena.session_id if sena else None},
            "llm": llm_health,
            "memory": memory_status,
            "extensions": extensions_status,
            "websocket": {
                "connections": ws_manager.connection_count,
            },
        },
    }

    if status != "healthy":
        return JSONResponse(status_code=503, content=response)

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
        "uptime_seconds": uptime,
        "start_time": _start_time.isoformat(),
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
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await ws_manager.disconnect(client_id)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"=== UNHANDLED EXCEPTION ===")
    logger.error(f"URL: {request.method} {request.url}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {exc}")
    logger.error(f"Full traceback:", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc),
            "type": type(exc).__name__,
        }
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