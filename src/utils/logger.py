# src/utils/logger.py
"""
Centralized Logging System for Sena

Uses loguru for advanced logging with:
- Console output with colors
- File rotation
- Session-based logging
- Structured logging support
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger as _loguru_logger

# Export the logger instance directly
logger = _loguru_logger

# Remove default handler
logger.remove()

# Global state for log level
_current_level = "INFO"
_initialized = False


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    session_dir: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "1 week",
) -> None:
    """
    Setup the logging system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to the main log file
        session_dir: Directory for session logs
        rotation: When to rotate log files
        retention: How long to keep old logs
    """
    global _current_level, _initialized

    # Clear existing handlers
    logger.remove()

    _current_level = level.upper()

    # Console handler — clean format, no module path noise
    logger.add(
        sys.stderr,
        level=_current_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            level=_current_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

    # Session handler (one file per session/day)
    if session_dir:
        session_path = Path(session_dir)
        session_path.mkdir(parents=True, exist_ok=True)

        session_file = session_path / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logger.add(
            str(session_file),
            level="DEBUG",  # Session logs capture everything
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days",
            compression="zip",
        )

    _initialized = True
    logger.info(f"Logging initialized at level {_current_level}")


def get_logger(name: str) -> Any:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the module

    Returns:
        Logger instance bound to the module name
    """
    return logger.bind(name=name)


class LogContext:
    """
    Context manager for adding context to log messages.

    Usage:
        with LogContext(user_id="123", session_id="abc"):
            logger.info("Processing request")
    """

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self._token: Any = None

    def __enter__(self) -> "LogContext":
        self._token = logger.contextualize(**self.context)
        self._token.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token:
            self._token.__exit__(*args)


def log_exception(exc: Exception, context: Optional[dict[str, Any]] = None) -> None:
    """
    Log an exception with context.

    Args:
        exc: The exception to log
        context: Additional context information
    """
    context = context or {}
    logger.opt(exception=True).error(f"Exception occurred: {type(exc).__name__}: {exc}", **context)


# Convenience functions for structured logging
def log_event(event_type: str, data: dict[str, Any], level: str = "INFO") -> None:
    """
    Log a structured event.

    Args:
        event_type: Type of the event
        data: Event data
        level: Log level
    """
    log_func = getattr(logger, level.lower())
    log_func(f"[{event_type}] {data}")


def log_performance(
    operation: str,
    duration_ms: float,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log performance metrics.

    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        metadata: Additional metadata
    """
    metadata = metadata or {}
    logger.debug(f"[PERF] {operation}: {duration_ms:.2f}ms | {metadata}")


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
) -> None:
    """
    Log LLM API call.

    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration_ms: Call duration in milliseconds
    """
    logger.info(
        f"[LLM] Model: {model} | Prompt: {prompt_tokens} tokens | "
        f"Completion: {completion_tokens} tokens | Duration: {duration_ms:.2f}ms"
    )


def log_memory_operation(
    operation: str,
    memory_type: str,
    count: int,
    duration_ms: float,
) -> None:
    """
    Log memory system operation.

    Args:
        operation: Operation type (store, retrieve, etc.)
        memory_type: Type of memory (short_term, long_term)
        count: Number of items affected
        duration_ms: Operation duration in milliseconds
    """
    logger.debug(f"[MEMORY] {operation.upper()} | Type: {memory_type} | Count: {count} | Duration: {duration_ms:.2f}ms")


def log_extension_event(
    extension_name: str,
    event: str,
    success: bool,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log extension event.

    Args:
        extension_name: Name of the extension
        event: Event type (load, execute, reload, etc.)
        success: Whether the operation was successful
        duration_ms: Operation duration in milliseconds
        error: Error message if failed
    """
    status = "SUCCESS" if success else "FAILED"
    msg = f"[EXTENSION] {extension_name} | {event.upper()} | {status}"

    if duration_ms is not None:
        msg += f" | {duration_ms:.2f}ms"

    if error:
        msg += f" | Error: {error}"

    if success:
        logger.debug(msg)
    else:
        logger.warning(msg)
