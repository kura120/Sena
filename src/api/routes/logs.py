# src/api/routes/logs.py
"""Logs API endpoints for retrieving structured log data."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, HTTPException, Query

from src.config.settings import get_app_data_dir

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


@router.post(
    "/clear",
    response_model=dict,
    summary="Clear logs",
    description="Delete stored log files (both main and session logs).",
)
async def clear_logs():
    deleted_files: list[str] = []
    for log_file in _iter_log_files():
        try:
            log_file.unlink()
            deleted_files.append(log_file.name)
        except FileNotFoundError:
            continue
    if not deleted_files:
        return {"status": "noop", "deleted": []}
    return {"status": "success", "deleted": deleted_files}
