# src/api/routes/settings.py
"""
Settings API routes.

Covers all settings sections (LLM, memory, database, logging, API, extensions,
telemetry, bootstrapper, UI) and persists changes to the correct settings.yaml
path in both development and production (PyInstaller) environments.
"""

from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config.settings import get_config_path, get_settings, reload_settings
from src.utils.logger import logger

router = APIRouter(prefix="/settings", tags=["Settings"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LLMSettingsRequest(BaseModel):
    """Partial update for LLM settings."""

    provider: Optional[str] = Field(None, description="LLM provider (e.g., ollama)")
    base_url: Optional[str] = Field(None, description="Provider base URL")
    timeout: Optional[int] = Field(None, ge=1, description="Request timeout in seconds")
    allow_runtime_switch: Optional[bool] = Field(None, description="Allow switching models at runtime")
    switch_cooldown: Optional[int] = Field(None, ge=0, description="Cooldown between model switches (seconds)")
    # Named model slots
    fast: Optional[str] = Field(None, description="Fast-response model name")
    critical: Optional[str] = Field(None, description="Critical/thinking model name")
    code: Optional[str] = Field(None, description="Coding model name")
    router: Optional[str] = Field(None, description="Router model name")


class MemorySettingsRequest(BaseModel):
    """Partial update for memory settings."""

    provider: Optional[str] = Field(None, description="Memory provider (e.g., mem0)")
    short_term_max_messages: Optional[int] = Field(None, ge=1, description="Max messages in short-term buffer")
    short_term_expire_after: Optional[int] = Field(None, ge=0, description="Short-term expiry in seconds")
    long_term_auto_extract: Optional[bool] = Field(None, description="Auto-extract learnings")
    long_term_extract_interval: Optional[int] = Field(None, ge=1, description="Extract interval (messages)")
    retrieval_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Min similarity threshold")
    retrieval_max_results: Optional[int] = Field(None, ge=1, le=100, description="Max retrieval results")
    retrieval_reranking: Optional[bool] = Field(None, description="Enable retrieval reranking")
    embeddings_model: Optional[str] = Field(None, description="Embedding model name")

    # Personality fields
    personality_inferential_learning_enabled: Optional[bool] = Field(None, description="Enable inferential learning")
    personality_inferential_learning_requires_approval: Optional[bool] = Field(
        None, description="Require approval for inferred fragments"
    )
    personality_auto_approve_enabled: Optional[bool] = Field(None, description="Enable auto-approval")
    personality_auto_approve_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Auto-approve confidence threshold"
    )
    personality_learning_mode: Optional[str] = Field(
        None, description="Learning mode: conservative | moderate | aggressive"
    )
    personality_token_budget: Optional[int] = Field(
        None, ge=64, le=4096, description="Token budget for personality block"
    )
    personality_max_fragments_in_prompt: Optional[int] = Field(
        None, ge=1, le=100, description="Max fragments injected into system prompt"
    )
    personality_compress_threshold: Optional[int] = Field(
        None, ge=5, le=500, description="Fragment count before compression"
    )


class LoggingSettingsRequest(BaseModel):
    """Partial update for logging settings."""

    level: Optional[str] = Field(None, description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    file_enabled: Optional[bool] = Field(None, description="Enable file logging")
    session_enabled: Optional[bool] = Field(None, description="Enable session logging")
    database_level: Optional[str] = Field(None, description="SQLAlchemy log level")


class TelemetrySettingsRequest(BaseModel):
    """Partial update for telemetry settings."""

    enabled: Optional[bool] = Field(None, description="Enable telemetry collection")
    collect_interval: Optional[int] = Field(None, ge=1, description="Metrics collection interval (seconds)")
    retention_days: Optional[int] = Field(None, ge=1, description="Metrics retention period (days)")
    track_response_times: Optional[bool] = Field(None)
    track_memory_usage: Optional[bool] = Field(None)
    track_extension_performance: Optional[bool] = Field(None)


class UISettingsRequest(BaseModel):
    """Partial update for UI settings."""

    auto_open_browser: Optional[bool] = Field(None, description="Open browser on startup")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _persist(settings) -> str:
    """Save settings to the correct config file and bust the cache."""
    path = get_config_path()
    settings.to_yaml(path)
    reload_settings()
    return str(path)


# ---------------------------------------------------------------------------
# GET — read current values for each section
# ---------------------------------------------------------------------------


@router.get(
    "/llm",
    response_model=dict[str, Any],
    summary="Get LLM settings",
    description="Returns the current LLM provider, base URL, and model assignments",
)
async def get_llm_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        models = {slot: (cfg.name if cfg else None) for slot, cfg in s.llm.models.items()}
        return {
            "status": "success",
            "data": {
                "provider": s.llm.provider,
                "base_url": s.llm.base_url,
                "timeout": s.llm.timeout,
                "allow_runtime_switch": s.llm.allow_runtime_switch,
                "switch_cooldown": s.llm.switch_cooldown,
                "models": models,
            },
        }
    except Exception as e:
        logger.error(f"Get LLM settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/memory",
    response_model=dict[str, Any],
    summary="Get memory settings",
    description="Returns the current memory configuration",
)
async def get_memory_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        m = s.memory
        p = m.personality
        return {
            "status": "success",
            "data": {
                "provider": m.provider,
                "embeddings_model": m.embeddings.model,
                "short_term": {
                    "max_messages": m.short_term.max_messages,
                    "expire_after": m.short_term.expire_after,
                },
                "long_term": {
                    "auto_extract": m.long_term.auto_extract,
                    "extract_interval": m.long_term.extract_interval,
                },
                "retrieval": {
                    "dynamic_threshold": m.retrieval.dynamic_threshold,
                    "max_results": m.retrieval.max_results,
                    "reranking": m.retrieval.reranking,
                },
                "personality": {
                    "inferential_learning_enabled": p.inferential_learning_enabled,
                    "inferential_learning_requires_approval": p.inferential_learning_requires_approval,
                    "auto_approve_enabled": p.auto_approve_enabled,
                    "auto_approve_threshold": p.auto_approve_threshold,
                    "learning_mode": p.learning_mode,
                    "personality_token_budget": p.personality_token_budget,
                    "max_fragments_in_prompt": p.max_fragments_in_prompt,
                    "compress_threshold": p.compress_threshold,
                },
            },
        }
    except Exception as e:
        logger.error(f"Get memory settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/logging",
    response_model=dict[str, Any],
    summary="Get logging settings",
    description="Returns the current logging configuration",
)
async def get_logging_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        lg = s.logging
        return {
            "status": "success",
            "data": {
                "level": lg.level,
                "database_level": lg.database_level,
                "file": {
                    "enabled": lg.file.enabled,
                    "path": lg.file.path,
                },
                "session": {
                    "enabled": lg.session.enabled,
                    "path": lg.session.path,
                },
            },
        }
    except Exception as e:
        logger.error(f"Get logging settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/telemetry",
    response_model=dict[str, Any],
    summary="Get telemetry settings",
    description="Returns the current telemetry configuration",
)
async def get_telemetry_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        t = s.telemetry
        return {
            "status": "success",
            "data": {
                "enabled": t.enabled,
                "metrics": {
                    "collect_interval": t.metrics.collect_interval,
                    "retention_days": t.metrics.retention_days,
                },
                "performance": {
                    "track_response_times": t.performance.track_response_times,
                    "track_memory_usage": t.performance.track_memory_usage,
                    "track_extension_performance": t.performance.track_extension_performance,
                },
            },
        }
    except Exception as e:
        logger.error(f"Get telemetry settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ui",
    response_model=dict[str, Any],
    summary="Get UI settings",
    description="Returns the current UI configuration",
)
async def get_ui_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        return {
            "status": "success",
            "data": {
                "behind_the_sena_port": s.ui.behind_the_sena_port,
                "sena_app_port": s.ui.sena_app_port,
                "auto_open_browser": s.ui.auto_open_browser,
            },
        }
    except Exception as e:
        logger.error(f"Get UI settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/all",
    response_model=dict[str, Any],
    summary="Get all settings",
    description="Returns the full settings dump (all sections)",
)
async def get_all_settings() -> dict[str, Any]:
    try:
        s = get_settings()
        return {
            "status": "success",
            "data": s.model_dump(),
            "config_path": str(get_config_path()),
        }
    except Exception as e:
        logger.error(f"Get all settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST — update and persist individual sections
# ---------------------------------------------------------------------------


@router.post(
    "/llm",
    response_model=dict[str, Any],
    summary="Update LLM settings",
    description="Updates LLM provider, base URL, timeout, and model assignments. Persists to settings.yaml.",
)
async def update_llm_settings(payload: LLMSettingsRequest) -> dict[str, Any]:
    try:
        s = get_settings()

        if payload.provider is not None:
            s.llm.provider = payload.provider
        if payload.base_url is not None:
            s.llm.base_url = payload.base_url
        if payload.timeout is not None:
            s.llm.timeout = payload.timeout
        if payload.allow_runtime_switch is not None:
            s.llm.allow_runtime_switch = payload.allow_runtime_switch
        if payload.switch_cooldown is not None:
            s.llm.switch_cooldown = payload.switch_cooldown

        # Named model slots
        for slot, value in {
            "fast": payload.fast,
            "critical": payload.critical,
            "code": payload.code,
            "router": payload.router,
        }.items():
            if value is not None and slot in s.llm.models:
                s.llm.models[slot].name = value

        saved_path = _persist(s)
        logger.info(f"LLM settings updated and saved to {saved_path}")

        return {
            "status": "success",
            "message": "LLM settings updated",
            "config_path": saved_path,
        }
    except Exception as e:
        logger.error(f"Update LLM settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/memory",
    response_model=dict[str, Any],
    summary="Update memory settings",
    description="Updates memory configuration and persists to settings.yaml.",
)
async def update_memory_settings(payload: MemorySettingsRequest) -> dict[str, Any]:
    try:
        s = get_settings()
        m = s.memory

        if payload.provider is not None:
            m.provider = payload.provider
        if payload.embeddings_model is not None:
            m.embeddings.model = payload.embeddings_model
        if payload.short_term_max_messages is not None:
            m.short_term.max_messages = payload.short_term_max_messages
        if payload.short_term_expire_after is not None:
            m.short_term.expire_after = payload.short_term_expire_after
        if payload.long_term_auto_extract is not None:
            m.long_term.auto_extract = payload.long_term_auto_extract
        if payload.long_term_extract_interval is not None:
            m.long_term.extract_interval = payload.long_term_extract_interval
        if payload.retrieval_threshold is not None:
            m.retrieval.dynamic_threshold = payload.retrieval_threshold
        if payload.retrieval_max_results is not None:
            m.retrieval.max_results = payload.retrieval_max_results
        if payload.retrieval_reranking is not None:
            m.retrieval.reranking = payload.retrieval_reranking

        # Personality fields
        p = m.personality
        if payload.personality_inferential_learning_enabled is not None:
            p.inferential_learning_enabled = payload.personality_inferential_learning_enabled
        if payload.personality_inferential_learning_requires_approval is not None:
            p.inferential_learning_requires_approval = payload.personality_inferential_learning_requires_approval
        if payload.personality_auto_approve_enabled is not None:
            p.auto_approve_enabled = payload.personality_auto_approve_enabled
        if payload.personality_auto_approve_threshold is not None:
            p.auto_approve_threshold = payload.personality_auto_approve_threshold
        if payload.personality_learning_mode is not None:
            p.learning_mode = payload.personality_learning_mode
        if payload.personality_token_budget is not None:
            p.personality_token_budget = payload.personality_token_budget
        if payload.personality_max_fragments_in_prompt is not None:
            p.max_fragments_in_prompt = payload.personality_max_fragments_in_prompt
        if payload.personality_compress_threshold is not None:
            p.compress_threshold = payload.personality_compress_threshold

        saved_path = _persist(s)
        logger.info(f"Memory settings updated and saved to {saved_path}")

        return {
            "status": "success",
            "message": "Memory settings updated",
            "config_path": saved_path,
        }
    except Exception as e:
        logger.error(f"Update memory settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/logging",
    response_model=dict[str, Any],
    summary="Update logging settings",
    description="Updates logging configuration and persists to settings.yaml.",
)
async def update_logging_settings(payload: LoggingSettingsRequest) -> dict[str, Any]:
    try:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        s = get_settings()
        lg = s.logging

        if payload.level is not None:
            level = payload.level.upper()
            if level not in valid_levels:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid log level '{payload.level}'. Must be one of: {sorted(valid_levels)}",
                )
            lg.level = level
        if payload.database_level is not None:
            db_level = payload.database_level.upper()
            if db_level not in valid_levels:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid database log level '{payload.database_level}'.",
                )
            lg.database_level = db_level
        if payload.file_enabled is not None:
            lg.file.enabled = payload.file_enabled
        if payload.session_enabled is not None:
            lg.session.enabled = payload.session_enabled

        saved_path = _persist(s)
        logger.info(f"Logging settings updated and saved to {saved_path}")

        return {
            "status": "success",
            "message": "Logging settings updated",
            "config_path": saved_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update logging settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/telemetry",
    response_model=dict[str, Any],
    summary="Update telemetry settings",
    description="Updates telemetry configuration and persists to settings.yaml.",
)
async def update_telemetry_settings(payload: TelemetrySettingsRequest) -> dict[str, Any]:
    try:
        s = get_settings()
        t = s.telemetry

        if payload.enabled is not None:
            t.enabled = payload.enabled
        if payload.collect_interval is not None:
            t.metrics.collect_interval = payload.collect_interval
        if payload.retention_days is not None:
            t.metrics.retention_days = payload.retention_days
        if payload.track_response_times is not None:
            t.performance.track_response_times = payload.track_response_times
        if payload.track_memory_usage is not None:
            t.performance.track_memory_usage = payload.track_memory_usage
        if payload.track_extension_performance is not None:
            t.performance.track_extension_performance = payload.track_extension_performance

        saved_path = _persist(s)
        logger.info(f"Telemetry settings updated and saved to {saved_path}")

        return {
            "status": "success",
            "message": "Telemetry settings updated",
            "config_path": saved_path,
        }
    except Exception as e:
        logger.error(f"Update telemetry settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/ui",
    response_model=dict[str, Any],
    summary="Update UI settings",
    description="Updates UI configuration and persists to settings.yaml.",
)
async def update_ui_settings(payload: UISettingsRequest) -> dict[str, Any]:
    try:
        s = get_settings()

        if payload.auto_open_browser is not None:
            s.ui.auto_open_browser = payload.auto_open_browser

        saved_path = _persist(s)
        logger.info(f"UI settings updated and saved to {saved_path}")

        return {
            "status": "success",
            "message": "UI settings updated",
            "config_path": saved_path,
        }
    except Exception as e:
        logger.error(f"Update UI settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Ollama helpers (requires internet / local Ollama)
# @RequiresInternet: Ollama API at configured base_url
# @Graceful: Returns 502 with clear message if Ollama is unreachable
# ---------------------------------------------------------------------------


@router.get(
    "/ollama/models",
    response_model=dict[str, Any],
    summary="List available Ollama models",
    description="Fetches available models from the configured Ollama instance. Requires Ollama to be running.",
)
async def list_ollama_models() -> dict[str, Any]:
    """
    @RequiresInternet: Ollama API (localhost by default, but may be remote)
    @Graceful: Returns 502 with a user-friendly message if unreachable
    """
    try:
        s = get_settings()
        base_url = s.llm.base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()

        models = response.json().get("models", [])
        names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]

        return {
            "status": "success",
            "provider": "ollama",
            "base_url": base_url,
            "models": names,
            "count": len(names),
        }
    except httpx.ConnectError:
        logger.warning("Ollama is not reachable at configured base_url")
        raise HTTPException(
            status_code=502,
            detail="Ollama is not running or not reachable. Start Ollama and try again.",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned an error: {e}")
        raise HTTPException(status_code=502, detail=f"Ollama API error: {e.response.status_code}")
    except httpx.TimeoutException:
        logger.warning("Ollama request timed out")
        raise HTTPException(status_code=504, detail="Ollama request timed out. Is Ollama running?")
    except Exception as e:
        logger.error(f"List Ollama models error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ollama/health",
    response_model=dict[str, Any],
    summary="Check Ollama connectivity",
    description="Pings the configured Ollama instance to verify it is reachable.",
)
async def check_ollama_health() -> dict[str, Any]:
    """
    @RequiresInternet: Ollama API
    @Graceful: Returns connected=false with reason if unreachable
    """
    try:
        s = get_settings()
        base_url = s.llm.base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            reachable = response.status_code == 200

        return {
            "status": "success",
            "connected": reachable,
            "base_url": base_url,
        }
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        s = get_settings()
        return {
            "status": "success",
            "connected": False,
            "base_url": s.llm.base_url,
            "reason": "Ollama is not running or not reachable",
        }
    except Exception as e:
        logger.error(f"Ollama health check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
