# src/core/constants.py
"""
Constants and Enums for Sena

Defines all constant values used throughout the application.
"""

from enum import Enum, auto
from typing import Final

# ============================================
# Version Information
# ============================================
VERSION: Final[str] = "1.0.0"
APP_NAME: Final[str] = "Sena"


# ============================================
# Processing Stages
# ============================================
class ProcessingStage(str, Enum):
    """Stages in the request processing pipeline."""

    IDLE = "idle"
    RECEIVING = "receiving"
    INTENT_CLASSIFICATION = "intent_classification"
    MEMORY_RETRIEVAL = "memory_retrieval"
    EXTENSION_CHECK = "extension_check"
    EXTENSION_EXECUTION = "extension_execution"
    REASONING = "reasoning"
    LLM_PROCESSING = "llm_processing"
    LLM_STREAMING = "llm_streaming"
    POST_PROCESSING = "post_processing"
    MEMORY_STORAGE = "memory_storage"
    COMPLETE = "complete"
    ERROR = "error"


# ============================================
# Model Types
# ============================================
class ModelType(str, Enum):
    """Types of LLM models available."""

    FAST = "fast"
    CRITICAL = "critical"
    CODE = "code"
    ROUTER = "router"
    REASONING = "reasoning"


MODEL_TYPES: Final[list[str]] = [m.value for m in ModelType]


# ============================================
# Intent Types
# ============================================
class IntentType(str, Enum):
    """Types of user intents."""

    GREETING = "greeting"
    FAREWELL = "farewell"
    GENERAL_CONVERSATION = "general_conversation"
    QUESTION = "question"
    COMPLEX_QUERY = "complex_query"
    CODE_REQUEST = "code_request"
    CODE_EXPLANATION = "code_explanation"
    SYSTEM_COMMAND = "system_command"
    WEB_SEARCH = "web_search"
    FILE_OPERATION = "file_operation"
    MEMORY_RECALL = "memory_recall"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    MATH = "math"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    UNKNOWN = "unknown"


INTENT_TYPES: Final[list[str]] = [i.value for i in IntentType]


# ============================================
# Intent to Model Mapping
# ============================================
INTENT_MODEL_MAPPING: Final[dict[IntentType, ModelType]] = {
    IntentType.GREETING: ModelType.FAST,
    IntentType.FAREWELL: ModelType.FAST,
    IntentType.GENERAL_CONVERSATION: ModelType.FAST,
    IntentType.QUESTION: ModelType.FAST,
    IntentType.COMPLEX_QUERY: ModelType.CRITICAL,
    IntentType.CODE_REQUEST: ModelType.CODE,
    IntentType.CODE_EXPLANATION: ModelType.CODE,
    IntentType.SYSTEM_COMMAND: ModelType.FAST,
    IntentType.WEB_SEARCH: ModelType.FAST,
    IntentType.FILE_OPERATION: ModelType.FAST,
    IntentType.MEMORY_RECALL: ModelType.FAST,
    IntentType.CREATIVE_WRITING: ModelType.CRITICAL,
    IntentType.ANALYSIS: ModelType.CRITICAL,
    IntentType.MATH: ModelType.CRITICAL,
    IntentType.TRANSLATION: ModelType.FAST,
    IntentType.SUMMARIZATION: ModelType.CRITICAL,
    IntentType.UNKNOWN: ModelType.FAST,
}


# ============================================
# Intent to Extensions Mapping
# ============================================
INTENT_EXTENSION_MAPPING: Final[dict[IntentType, list[str]]] = {
    IntentType.SYSTEM_COMMAND: ["app_launcher", "system_info"],
    IntentType.WEB_SEARCH: ["web_search"],
    IntentType.FILE_OPERATION: ["file_search"],
}


# ============================================
# Intent Memory Requirements
# ============================================
INTENT_NEEDS_MEMORY: Final[dict[IntentType, bool]] = {
    IntentType.GREETING: False,
    IntentType.FAREWELL: False,
    IntentType.GENERAL_CONVERSATION: True,
    IntentType.QUESTION: True,
    IntentType.COMPLEX_QUERY: True,
    IntentType.CODE_REQUEST: True,
    IntentType.CODE_EXPLANATION: True,
    IntentType.SYSTEM_COMMAND: False,
    IntentType.WEB_SEARCH: False,
    IntentType.FILE_OPERATION: False,
    IntentType.MEMORY_RECALL: True,
    IntentType.CREATIVE_WRITING: True,
    IntentType.ANALYSIS: True,
    IntentType.MATH: False,
    IntentType.TRANSLATION: False,
    IntentType.SUMMARIZATION: True,
    IntentType.UNKNOWN: True,
}


# ============================================
# Memory Types
# ============================================
class MemoryType(str, Enum):
    """Types of memory storage."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


MEMORY_TYPES: Final[list[str]] = [m.value for m in MemoryType]


# ============================================
# Extension Status
# ============================================
class ExtensionStatus(str, Enum):
    """Status of an extension."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"
    VALIDATING = "validating"


# ============================================
# WebSocket Event Types
# ============================================
class WSEventType(str, Enum):
    """WebSocket event types."""

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"

    # Server -> Client
    PROCESSING_UPDATE = "processing_update"
    MEMORY_UPDATE = "memory_update"
    EXTENSION_UPDATE = "extension_update"
    LLM_THINKING = "llm_thinking"
    LOG = "log"
    ERROR = "error"
    PONG = "pong"
    STREAM_TOKEN = "stream_token"
    STREAM_END = "stream_end"


# ============================================
# Default Values
# ============================================
DEFAULT_TIMEOUT: Final[int] = 120
DEFAULT_MAX_TOKENS: Final[int] = 2048
DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_TOP_P: Final[float] = 0.9

# Short-term memory defaults
DEFAULT_SHORT_TERM_MAX_MESSAGES: Final[int] = 20
DEFAULT_SHORT_TERM_EXPIRE_SECONDS: Final[int] = 3600  # 1 hour

# Long-term memory defaults
DEFAULT_LONG_TERM_EXTRACT_INTERVAL: Final[int] = 10
DEFAULT_RETRIEVAL_MAX_RESULTS: Final[int] = 5
DEFAULT_RETRIEVAL_THRESHOLD: Final[float] = 0.6


# ============================================
# Error Messages
# ============================================
class ErrorMessages:
    """Standard error messages."""

    OLLAMA_NOT_RUNNING = "Ollama is not running. Please start Ollama and try again."
    MODEL_NOT_FOUND = "Model '{model}' is not available. Please install it with: ollama pull {model}"
    DATABASE_ERROR = "Database error occurred. Please try again."
    MEMORY_ERROR = "Memory system error. Continuing without memory context."
    EXTENSION_ERROR = "Extension '{extension}' failed to execute."
    TIMEOUT_ERROR = "Request timed out. Please try again."
    UNKNOWN_ERROR = "An unexpected error occurred. Please try again."
