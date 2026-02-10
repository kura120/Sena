# src/core/error_handler.py
"""
Global Error Handling System for Sena

Provides centralized error handling with:
- Automatic error logging
- Telemetry updates
- Recovery attempts
- User-friendly error messages
"""

import asyncio
import functools
import traceback
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, Union, Coroutine

from src.core.exceptions import (
    SenaException,
    LLMException,
    LLMConnectionError,
    LLMTimeoutError,
    MemoryException,
    ExtensionException,
    DatabaseException,
)
from src.utils.logger import logger, log_exception


T = TypeVar("T")


class ErrorContext:
    """
    Context information for error handling.
    
    Tracks the current state when an error occurs.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        user_input: Optional[str] = None,
        processing_stage: Optional[str] = None,
        model_used: Optional[str] = None,
        extensions_active: Optional[list[str]] = None,
    ):
        self.session_id = session_id
        self.user_input = user_input
        self.processing_stage = processing_stage
        self.model_used = model_used
        self.extensions_active = extensions_active or []
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "session_id": self.session_id,
            "user_input": self.user_input[:100] if self.user_input else None,  # Truncate
            "processing_stage": self.processing_stage,
            "model_used": self.model_used,
            "extensions_active": self.extensions_active,
            "timestamp": self.timestamp.isoformat(),
        }


class RecoveryStrategy:
    """
    Defines recovery strategies for different error types.
    """
    
    @staticmethod
    async def recover_llm_connection(error: LLMConnectionError, context: ErrorContext) -> Optional[str]:
        """
        Attempt to recover from LLM connection error.
        
        Strategy:
        1. Wait and retry
        2. If still failing, return cached response if available
        """
        logger.warning("Attempting LLM connection recovery...")
        
        # Wait a bit before retry
        await asyncio.sleep(2)
        
        # Return None to indicate retry should be attempted
        return None
    
    @staticmethod
    async def recover_llm_timeout(error: LLMTimeoutError, context: ErrorContext) -> Optional[str]:
        """
        Attempt to recover from LLM timeout.
        
        Strategy:
        1. Try with a smaller/faster model
        2. Reduce context size
        """
        logger.warning("Attempting LLM timeout recovery...")
        
        # Suggest using faster model
        return "fast"  # Return model type to switch to
    
    @staticmethod
    async def recover_memory_error(error: MemoryException, context: ErrorContext) -> bool:
        """
        Attempt to recover from memory error.
        
        Strategy:
        1. Continue without memory context
        """
        logger.warning("Memory system error - continuing without memory context")
        return True  # Continue without memory
    
    @staticmethod
    async def recover_extension_error(error: ExtensionException, context: ErrorContext) -> bool:
        """
        Attempt to recover from extension error.
        
        Strategy:
        1. Disable the problematic extension
        2. Continue without it
        """
        logger.warning(f"Extension error - disabling {error.extension_name}")
        return True  # Continue without extension


class ErrorHandler:
    """
    Centralized error handler for Sena.
    
    Handles all exceptions, logs them, updates telemetry,
    and attempts recovery when possible.
    """
    
    def __init__(self) -> None:
        self._error_counts: dict[str, int] = {}
        self._last_errors: list[dict[str, Any]] = []
        self._max_stored_errors = 100
        self._telemetry_callback: Optional[Callable[..., Coroutine[Any, Any, None]]] = None
        self._ws_broadcast_callback: Optional[Callable[..., Coroutine[Any, Any, None]]] = None
    
    def set_telemetry_callback(self, callback: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Set callback for telemetry updates."""
        self._telemetry_callback = callback
    
    def set_ws_broadcast_callback(self, callback: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Set callback for WebSocket broadcasts."""
        self._ws_broadcast_callback = callback
    
    async def handle(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        reraise: bool = True,
    ) -> Optional[Any]:
        """
        Handle an exception.
        
        Args:
            error: The exception to handle
            context: Error context information
            reraise: Whether to reraise the exception after handling
            
        Returns:
            Recovery result if successful, None otherwise
        """
        context = context or ErrorContext()
        
        # Log the error
        self._log_error(error, context)
        
        # Update error counts
        error_type = type(error).__name__
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        # Store error for history
        self._store_error(error, context)
        
        # Update telemetry
        await self._update_telemetry(error, context)
        
        # Broadcast to WebSocket clients
        await self._broadcast_error(error, context)
        
        # Attempt recovery for recoverable errors
        if isinstance(error, SenaException) and error.recoverable:
            recovery_result = await self._attempt_recovery(error, context)
            if recovery_result is not None:
                return recovery_result
        
        # Reraise if requested
        if reraise:
            raise error
        
        return None
    
    def _log_error(self, error: Exception, context: ErrorContext) -> None:
        """Log the error with full context."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context.to_dict(),
        }
        
        if isinstance(error, SenaException):
            error_data["error_code"] = error.code
            error_data["error_context"] = error.context
            error_data["recoverable"] = error.recoverable
        
        log_exception(error, error_data)
    
    def _store_error(self, error: Exception, context: ErrorContext) -> None:
        """Store error in history."""
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context.to_dict(),
            "stack_trace": traceback.format_exc(),
        }
        
        if isinstance(error, SenaException):
            error_record["error_code"] = error.code
        
        self._last_errors.append(error_record)
        
        # Trim old errors
        if len(self._last_errors) > self._max_stored_errors:
            self._last_errors = self._last_errors[-self._max_stored_errors:]
    
    async def _update_telemetry(self, error: Exception, context: ErrorContext) -> None:
        """Update telemetry with error information."""
        if self._telemetry_callback:
            try:
                await self._telemetry_callback(
                    event_type="error",
                    data={
                        "error_type": type(error).__name__,
                        "processing_stage": context.processing_stage,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update telemetry: {e}")
    
    async def _broadcast_error(self, error: Exception, context: ErrorContext) -> None:
        """Broadcast error to WebSocket clients."""
        if self._ws_broadcast_callback:
            try:
                await self._ws_broadcast_callback(
                    event_type="error",
                    data={
                        "error_type": type(error).__name__,
                        "message": str(error),
                        "recoverable": isinstance(error, SenaException) and error.recoverable,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast error: {e}")
    
    async def _attempt_recovery(
        self,
        error: SenaException,
        context: ErrorContext,
    ) -> Optional[Any]:
        """
        Attempt to recover from a recoverable error.
        
        Args:
            error: The recoverable exception
            context: Error context
            
        Returns:
            Recovery result if successful, None otherwise
        """
        try:
            if isinstance(error, LLMConnectionError):
                return await RecoveryStrategy.recover_llm_connection(error, context)
            elif isinstance(error, LLMTimeoutError):
                return await RecoveryStrategy.recover_llm_timeout(error, context)
            elif isinstance(error, MemoryException):
                return await RecoveryStrategy.recover_memory_error(error, context)
            elif isinstance(error, ExtensionException):
                return await RecoveryStrategy.recover_extension_error(error, context)
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
        
        return None
    
    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        return {
            "error_counts": self._error_counts.copy(),
            "total_errors": sum(self._error_counts.values()),
            "recent_errors": len(self._last_errors),
        }
    
    def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent error history."""
        return self._last_errors[-limit:]
    
    def clear_history(self) -> None:
        """Clear error history."""
        self._last_errors.clear()
        self._error_counts.clear()


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    reraise: bool = True,
    default_return: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for automatic error handling.
    
    Args:
        reraise: Whether to reraise exceptions after handling
        default_return: Default value to return on error if not reraising
    
    Usage:
        @handle_errors()
        async def my_function():
            ...
            
        @handle_errors(reraise=False, default_return="Error occurred")
        async def my_other_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    result = await error_handler.handle(e, context=None, reraise=reraise)
                    if not reraise:
                        return result if result is not None else default_return
                    return result
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Run async handler in sync context
                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(
                            error_handler.handle(e, context=None, reraise=reraise)
                        )
                    finally:
                        loop.close()
                    
                    if not reraise:
                        return result if result is not None else default_return
                    return result
            return sync_wrapper  # type: ignore
    
    return decorator