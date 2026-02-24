# src/core/exceptions.py
"""
Exception Hierarchy for Sena

Defines all custom exceptions used throughout the application.
"""

from typing import Any, Optional


class SenaException(Exception):
    """
    Base exception for all Sena errors.
    
    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        context: Additional context about the error
        recoverable: Whether the error can be automatically recovered from
    """
    
    def __init__(
        self,
        message: str,
        code: str = "SENA_ERROR",
        context: Optional[dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or {}
        self.recoverable = recoverable
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error": self.code,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
        }
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ============================================
# LLM Exceptions
# ============================================
class LLMException(SenaException):
    """Base exception for LLM-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "LLM_ERROR",
        model: Optional[str] = None,
        **kwargs: Any,
    ):
        context = kwargs.pop("context", {})
        if model:
            context["model"] = model
        super().__init__(message, code=code, context=context, **kwargs)
        self.model = model


class LLMConnectionError(LLMException):
    """Raised when connection to LLM service fails."""
    
    def __init__(self, message: str = "Failed to connect to LLM service", **kwargs: Any):
        super().__init__(message, code="LLM_CONNECTION_ERROR", recoverable=True, **kwargs)


class LLMTimeoutError(LLMException):
    """Raised when LLM request times out."""
    
    def __init__(self, message: str = "LLM request timed out", **kwargs: Any):
        super().__init__(message, code="LLM_TIMEOUT", recoverable=True, **kwargs)


class LLMModelNotFoundError(LLMException):
    """Raised when requested model is not available."""
    
    def __init__(self, model: str, **kwargs: Any):
        message = f"Model '{model}' not found. Please install it with: ollama pull {model}"
        super().__init__(message, code="LLM_MODEL_NOT_FOUND", model=model, **kwargs)


class LLMGenerationError(LLMException):
    """Raised when LLM fails to generate a response."""
    
    def __init__(self, message: str = "Failed to generate response", **kwargs: Any):
        super().__init__(message, code="LLM_GENERATION_ERROR", recoverable=True, **kwargs)


class LLMContextLengthError(LLMException):
    """Raised when input exceeds model's context window."""
    
    def __init__(self, model: str, max_tokens: int, actual_tokens: int, **kwargs: Any):
        message = f"Input ({actual_tokens} tokens) exceeds context window ({max_tokens} tokens)"
        context = kwargs.pop("context", {})
        context.update({"max_tokens": max_tokens, "actual_tokens": actual_tokens})
        super().__init__(message, code="LLM_CONTEXT_LENGTH_ERROR", model=model, context=context, **kwargs)


# ============================================
# Memory Exceptions
# ============================================
class MemoryException(SenaException):
    """Base exception for memory system errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "MEMORY_ERROR",
        memory_type: Optional[str] = None,
        **kwargs: Any,
    ):
        context = kwargs.pop("context", {})
        if memory_type:
            context["memory_type"] = memory_type
        super().__init__(message, code=code, context=context, **kwargs)
        self.memory_type = memory_type


class MemoryStorageError(MemoryException):
    """Raised when storing memory fails."""
    
    def __init__(self, message: str = "Failed to store memory", **kwargs: Any):
        super().__init__(message, code="MEMORY_STORAGE_ERROR", recoverable=True, **kwargs)


class MemoryRetrievalError(MemoryException):
    """Raised when retrieving memory fails."""
    
    def __init__(self, message: str = "Failed to retrieve memory", **kwargs: Any):
        super().__init__(message, code="MEMORY_RETRIEVAL_ERROR", recoverable=True, **kwargs)


class MemoryEmbeddingError(MemoryException):
    """Raised when generating embeddings fails."""
    
    def __init__(self, message: str = "Failed to generate embeddings", **kwargs: Any):
        super().__init__(message, code="MEMORY_EMBEDDING_ERROR", recoverable=True, **kwargs)


class VectorDBError(MemoryException):
    """Raised when vector database operations fail."""
    
    def __init__(self, message: str = "Vector database error", **kwargs: Any):
        super().__init__(message, code="VECTOR_DB_ERROR", recoverable=True, **kwargs)


# ============================================
# Extension Exceptions
# ============================================
class ExtensionException(SenaException):
    """Base exception for extension-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "EXTENSION_ERROR",
        extension_name: Optional[str] = None,
        **kwargs: Any,
    ):
        context = kwargs.pop("context", {})
        if extension_name:
            context["extension"] = extension_name
        super().__init__(message, code=code, context=context, **kwargs)
        self.extension_name = extension_name


class ExtensionNotFoundError(ExtensionException):
    """Raised when extension is not found."""
    
    def __init__(self, extension_name: str, **kwargs: Any):
        message = f"Extension '{extension_name}' not found"
        super().__init__(message, code="EXTENSION_NOT_FOUND", extension_name=extension_name, **kwargs)


class ExtensionLoadError(ExtensionException):
    """Raised when extension fails to load."""
    
    def __init__(self, extension_name: str, reason: str = "", **kwargs: Any):
        message = f"Failed to load extension '{extension_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, code="EXTENSION_LOAD_ERROR", extension_name=extension_name, recoverable=True, **kwargs)


class ExtensionValidationError(ExtensionException):
    """Raised when extension fails validation."""
    
    def __init__(self, extension_name: str, violations: list[str], **kwargs: Any):
        message = f"Extension '{extension_name}' failed validation: {', '.join(violations)}"
        context = kwargs.pop("context", {})
        context["violations"] = violations
        super().__init__(message, code="EXTENSION_VALIDATION_ERROR", extension_name=extension_name, context=context, **kwargs)


class ExtensionExecutionError(ExtensionException):
    """Raised when extension execution fails."""
    
    def __init__(self, extension_name: str, reason: str = "", **kwargs: Any):
        message = f"Extension '{extension_name}' execution failed"
        if reason:
            message += f": {reason}"
        super().__init__(message, code="EXTENSION_EXECUTION_ERROR", extension_name=extension_name, recoverable=True, **kwargs)


class ExtensionTimeoutError(ExtensionException):
    """Raised when extension execution times out."""
    
    def __init__(self, extension_name: str, timeout: float, **kwargs: Any):
        message = f"Extension '{extension_name}' timed out after {timeout}s"
        context = kwargs.pop("context", {})
        context["timeout"] = timeout
        super().__init__(message, code="EXTENSION_TIMEOUT", extension_name=extension_name, context=context, recoverable=True, **kwargs)


class ExtensionSecurityError(ExtensionException):
    """Raised when extension violates security policy."""
    
    def __init__(self, extension_name: str, violation: str, **kwargs: Any):
        message = f"Extension '{extension_name}' security violation: {violation}"
        context = kwargs.pop("context", {})
        context["violation"] = violation
        super().__init__(message, code="EXTENSION_SECURITY_ERROR", extension_name=extension_name, context=context, **kwargs)


# ============================================
# Database Exceptions
# ============================================
class DatabaseException(SenaException):
    """Base exception for database errors."""
    
    def __init__(self, message: str, code: str = "DATABASE_ERROR", **kwargs: Any):
        super().__init__(message, code=code, **kwargs)


class DatabaseConnectionError(DatabaseException):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = "Failed to connect to database", **kwargs: Any):
        super().__init__(message, code="DATABASE_CONNECTION_ERROR", recoverable=True, **kwargs)


class DatabaseQueryError(DatabaseException):
    """Raised when database query fails."""
    
    def __init__(self, message: str = "Database query failed", query: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if query:
            context["query"] = query
        super().__init__(message, code="DATABASE_QUERY_ERROR", context=context, recoverable=True, **kwargs)


class DatabaseIntegrityError(DatabaseException):
    """Raised when database integrity is compromised."""
    
    def __init__(self, message: str = "Database integrity error", **kwargs: Any):
        super().__init__(message, code="DATABASE_INTEGRITY_ERROR", **kwargs)


class DatabaseMigrationError(DatabaseException):
    """Raised when database migration fails."""
    
    def __init__(self, message: str = "Database migration failed", version: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if version:
            context["version"] = version
        super().__init__(message, code="DATABASE_MIGRATION_ERROR", context=context, **kwargs)


# ============================================
# Bootstrap Exceptions
# ============================================
class BootstrapException(SenaException):
    """Base exception for bootstrap errors."""
    
    def __init__(self, message: str, code: str = "BOOTSTRAP_ERROR", check_name: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if check_name:
            context["check"] = check_name
        super().__init__(message, code=code, context=context, **kwargs)
        self.check_name = check_name


class OllamaNotRunningError(BootstrapException):
    """Raised when Ollama service is not running."""
    
    def __init__(self, **kwargs: Any):
        message = "Ollama is not running. Please start Ollama and try again."
        super().__init__(message, code="OLLAMA_NOT_RUNNING", check_name="ollama", **kwargs)


class ModelNotAvailableError(BootstrapException):
    """Raised when required model is not available."""
    
    def __init__(self, model: str, **kwargs: Any):
        message = f"Required model '{model}' is not available. Install with: ollama pull {model}"
        context = kwargs.pop("context", {})
        context["model"] = model
        super().__init__(message, code="MODEL_NOT_AVAILABLE", check_name="models", context=context, **kwargs)


# ============================================
# API Exceptions
# ============================================
class APIException(SenaException):
    """Base exception for API errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = 500,
        **kwargs: Any,
    ):
        super().__init__(message, code=code, **kwargs)
        self.status_code = status_code


class APIValidationError(APIException):
    """Raised when API request validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs: Any):
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        super().__init__(message, code="API_VALIDATION_ERROR", status_code=400, context=context, **kwargs)


class APIRateLimitError(APIException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60, **kwargs: Any):
        message = f"Rate limit exceeded. Retry after {retry_after} seconds."
        context = kwargs.pop("context", {})
        context["retry_after"] = retry_after
        super().__init__(message, code="API_RATE_LIMIT", status_code=429, context=context, **kwargs)


class WebSocketError(APIException):
    """Raised when WebSocket operation fails."""
    
    def __init__(self, message: str = "WebSocket error", **kwargs: Any):
        super().__init__(message, code="WEBSOCKET_ERROR", status_code=500, **kwargs)