# src/api/models/responses.py
"""API Response Models."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "details": {"field": "message", "issue": "cannot be empty"}
            }
        }


class ChatMetadata(BaseModel):
    """Metadata for chat response."""
    
    model_used: str = Field(..., description="Model that generated the response")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    intent: Optional[str] = Field(None, description="Detected intent type")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Intent confidence")
    extensions_used: list[str] = Field(default_factory=list, description="Extensions that were executed")
    tokens_used: int = Field(0, description="Tokens used in generation")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    
    response: str = Field(..., description="Generated response")
    session_id: str = Field(..., description="Session ID")
    metadata: ChatMetadata = Field(..., description="Response metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Hello! I'm doing well, thank you for asking.",
                "session_id": "abc123",
                "metadata": {
                    "model_used": "gemma2:2b",
                    "processing_time_ms": 1234.56,
                    "intent_type": "greeting",
                    "extensions_used": [],
                    "memory_retrieved": 0,
                }
            }
        }


class MemoryItem(BaseModel):
    """Single memory item."""
    
    memory_id: str = Field(..., description="Unique memory ID")
    content: str = Field(..., description="Memory content")
    category: Optional[str] = Field(None, description="Memory category")
    importance: int = Field(..., description="Importance score (1-10)")
    created_at: datetime = Field(..., description="When the memory was created")
    access_count: int = Field(0, description="Number of times accessed")
    relevance_score: Optional[float] = Field(None, description="Relevance score for search results")


class MemoryResponse(BaseModel):
    """Response model for memory operations."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    memory_id: Optional[str] = Field(None, description="Memory ID (for create/edit)")
    message: str = Field(..., description="Operation result message")


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""
    
    results: list[MemoryItem] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics."""
    
    total_memories: int = Field(..., description="Total number of memories")
    categories: dict[str, int] = Field(..., description="Count by category")
    avg_importance: float = Field(..., description="Average importance score")


class ExtensionItem(BaseModel):
    """Single extension item."""
    
    name: str = Field(..., description="Extension name")
    version: str = Field(..., description="Extension version")
    description: Optional[str] = Field(None, description="Extension description")
    extension_type: str = Field(..., description="Extension type (core, user, generated)")
    status: str = Field(..., description="Extension status (active, inactive, error)")
    execution_count: int = Field(0, description="Number of times executed")
    avg_execution_ms: float = Field(0, description="Average execution time in ms")
    error_count: int = Field(0, description="Number of errors")


class ExtensionListResponse(BaseModel):
    """Response model for extension list."""
    
    extensions: list[ExtensionItem] = Field(..., description="List of extensions")
    total: int = Field(..., description="Total number of extensions")


class ExtensionResponse(BaseModel):
    """Response model for extension operations."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    extension_name: Optional[str] = Field(None, description="Extension name")
    message: str = Field(..., description="Operation result message")
    code: Optional[str] = Field(default=None, description="Generated code (for generate endpoint)")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    components: dict[str, Any] = Field(..., description="Component health status")


class StatsResponse(BaseModel):
    """Response model for statistics."""
    
    session_id: str = Field(..., description="Current session ID")
    message_count: int = Field(..., description="Messages processed in session")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    llm_stats: dict[str, Any] = Field(..., description="LLM usage statistics")
    memory_stats: dict[str, Any] = Field(..., description="Memory statistics")
    telemetry: dict[str, Any] = Field(..., description="Telemetry data")


class ProcessingUpdate(BaseModel):
    """WebSocket processing update."""
    
    stage: str = Field(..., description="Current processing stage")
    details: str = Field("", description="Stage details")
    timestamp: datetime = Field(default_factory=datetime.now)


class LogEntry(BaseModel):
    """Log entry for streaming."""
    
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    logger_name: Optional[str] = Field(None, description="Logger name")
    timestamp: datetime = Field(default_factory=datetime.now)