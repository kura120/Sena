# src/api/routes/logs.py
"""Logs API endpoints for retrieving structured log data."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.config.settings import get_app_data_dir
from src.utils.logger import logger

# In-memory watermark set by clear_logs(). Any log entry whose timestamp is
# <= this value is hidden from all subsequent reads. Resets on process restart.
_cleared_at: str | None = None

router = APIRouter(prefix="/logs", tags=["Logs"])

LOG_DIR = get_app_data_dir() / "data" / "logs"
DEFAULT_LOG_FILE = LOG_DIR / "sena.log"
SESSION_DIR = LOG_DIR / "sessions"
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\|\s+"
    r"(?P<level>[A-Z]+)\s+\|\s+(?P<location>[^-]+)-\s+(?P<message>.*)$"
)
STRUCTURED_PATTERN = re.compile(r"^\[(?P<event>[A-Z_]+)\]\s+(?P<payload>\{.*\})$")
IGNORE_REQUEST_PATHS = ("/health", "/api/v1/logs")
IGNORE_SOURCES = ("log_requests",)


def _iter_log_files() -> list[Path]:
    files: list[Path] = []
    if DEFAULT_LOG_FILE.exists():
        files.append(DEFAULT_LOG_FILE)
    if SESSION_DIR.exists():
        session_files = sorted(SESSION_DIR.glob("session_*.log"), reverse=True)
        files.extend(session_files)
    return files


def _parse_line(line: str) -> dict | None:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    location = match.group("location").strip()
    message = match.group("message").strip()
    metadata = None
    event = None
    structured = STRUCTURED_PATTERN.match(message)
    if structured:
        event = structured.group("event").lower()
        payload = structured.group("payload")
        try:
            metadata = json.loads(payload)
        except json.JSONDecodeError:
            metadata = None
        message = f"{event} metadata"
    return {
        "timestamp": match.group("timestamp"),
        "level": match.group("level").lower(),
        "source": location,
        "message": message,
        "event": event,
        "metadata": metadata,
        "raw": line.strip(),
    }


def _load_logs(limit: int, level: str, source: str) -> list[dict]:
    entries: list[dict] = []
    for log_file in _iter_log_files():
        try:
            with log_file.open("r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            continue

        for line in reversed(lines):
            parsed = _parse_line(line)
            if not parsed:
                continue
            # Skip entries that predate the last clear() call. Because we
            # iterate newest-first, once we cross the watermark everything
            # remaining is also older — break early for efficiency.
            if _cleared_at and parsed["timestamp"] <= _cleared_at:
                break
            if any(source in parsed["source"].lower() for source in IGNORE_SOURCES):
                continue
            if parsed["message"].startswith(">>> REQUEST") or parsed["message"].startswith("<<< RESPONSE"):
                continue
            if any(path in parsed["message"] for path in IGNORE_REQUEST_PATHS):
                continue
            if level != "all" and parsed["level"] != level:
                continue
            if source != "all" and source.lower() not in parsed["source"].lower():
                continue
            entries.append(parsed)
            if len(entries) >= limit:
                return entries
    return entries


@router.get(
    "",
    response_model=dict,
    summary="Get system logs",
    description="Retrieve structured log entries captured by the logging subsystem.",
)
async def get_logs(
    level: str = Query("all", description="Filter by log level (all, info, warning, error, debug)"),
    source: str = Query("all", description="Filter by source component (module/function substring)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
):
    level = level.lower()
    if level not in {"all", "debug", "info", "warning", "error", "critical"}:
        raise HTTPException(status_code=400, detail="Invalid log level filter")

    entries = _load_logs(limit=limit, level=level, source=source)

    return {
        "logs": entries,
        "count": len(entries),
        "level_filter": level,
        "source_filter": source,
        "files": [f.name for f in _iter_log_files()],
    }


@router.get(
    "/sources",
    response_model=dict,
    summary="Get available log sources",
    description="Collect unique source entries from existing log files.",
)
async def get_log_sources():
    sources: set[str] = set()
    for log_file in _iter_log_files():
        try:
            with log_file.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    parsed = _parse_line(line)
                    if parsed:
                        sources.add(parsed["source"])
        except FileNotFoundError:
            continue

    return {
        "sources": sorted(sources),
        "count": len(sources),
    }


class SummarizeRequest(BaseModel):
    messages: list[str]


@router.post(
    "/summarize",
    response_model=dict,
    summary="Generate LLM summary for a log group",
    description=(
        "Given a list of raw log message strings (a process group's children), "
        "returns a concise one-line summary produced by the fast LLM model."
    ),
)
async def summarize_logs(body: SummarizeRequest) -> dict:
    """Generate a short summary for a collection of log lines using the fast model."""
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages list is empty")

    # Trim to at most 40 lines to keep the prompt small.
    lines = body.messages[:40]
    joined = "\n".join(f"- {m}" for m in lines)

    prompt = (
        "You are a concise log analyst. Given the following log lines from a single "
        "processing pipeline step, write ONE short summary sentence (max 15 words) "
        "that describes what happened. Do not include any preamble.\n\n"
        f"Log lines:\n{joined}\n\nSummary:"
    )

    summary = ""
    try:
        from src.api.deps import get_sena  # local import to avoid circular dep

        sena = await get_sena()
        if sena._llm_manager is None:
            raise RuntimeError("LLM manager not ready")
        raw = await sena._llm_manager.generate_simple(prompt=prompt, max_tokens=60)
        summary = raw.strip().strip('"').strip("'")
    except Exception as e:
        logger.warning(f"Log summarization failed: {e}")
        # Fallback: return first non-empty message truncated
        for m in lines:
            if m.strip():
                summary = m.strip()[:120]
                break

    return {"status": "success", "summary": summary or "Processing complete"}


@router.post(
    "/clear",
    response_model=dict,
    summary="Clear logs",
    description="Hide all current log entries by recording a cleared-at watermark. "
    "Session log files (not held open) are also deleted from disk.",
)
async def clear_logs():
    global _cleared_at

    # Record watermark — same millisecond-precision format loguru writes.
    _cleared_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:23]

    # Best-effort delete of session files (they are not held open by loguru).
    deleted_sessions: list[str] = []
    if SESSION_DIR.exists():
        for session_file in SESSION_DIR.glob("session_*.log"):
            try:
                session_file.unlink()
                deleted_sessions.append(session_file.name)
            except (FileNotFoundError, PermissionError, OSError):
                pass

    return {
        "status": "success",
        "cleared_at": _cleared_at,
        "deleted_sessions": deleted_sessions,
    }
