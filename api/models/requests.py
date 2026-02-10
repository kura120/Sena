# src/api/models/requests.py
"""API Request Models."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    
    message: str = Field(..., min_length=1, max_length=32000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    stream: bool = Field(False, description="Whether to stream the response")
    model_type: Optional[str] = Field(None, description="Force specific model type (fast, critical, code)")
    system_prompt: Optional[str] = Field(None, description="Override system prompt")
    mode: Optional[str] = Field("normal", description="Processing mode (normal, fast, critical)")
    extract_learnings: bool = Field(False, description="Extract and store learnings from conversation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello, how are you?",
                "session_id": "abc123",
                "stream": False,
            }
        }


class MemoryAddRequest(BaseModel):
    """Request model for adding memory."""
    
    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    category: Optional[str] = Field(None, description="Memory category")
    importance: int = Field(5, ge=1, le=10, description="Importance score (1-10)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "User prefers dark mode interfaces",
                "category": "preference",
                "importance": 7,
            }
        }


class MemoryEditRequest(BaseModel):
    """Request model for editing memory."""
    
    memory_id: str = Field(..., description="Memory ID to edit")
    content: Optional[str] = Field(None, description="New content")
    importance: Optional[int] = Field(None, ge=1, le=10, description="New importance score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "memory_id": "abc-123-def",
                "content": "Updated memory content",
                "importance": 8,
            }
        }


class MemorySearchRequest(BaseModel):
    """Request model for searching memories."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    category: Optional[str] = Field(None, description="Filter by category")
    min_importance: Optional[int] = Field(None, ge=1, le=10, description="Minimum importance score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "user preferences",
                "limit": 10,
            }
        }


class ExtensionGenerateRequest(BaseModel):
    """Request model for generating an extension."""
    
    description: str = Field(..., min_length=10, max_length=2000, description="Description of what the extension should do")
    name: Optional[str] = Field(None, description="Optional name for the extension")
    auto_enable: bool = Field(False, description="Whether to enable the extension automatically")
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Create an extension that gets the current weather for a given city",
                "name": "weather_lookup",
                "auto_enable": False,
            }
        }


class ExtensionToggleRequest(BaseModel):
    """Request model for toggling extension status."""
    
    enabled: bool = Field(..., description="Whether to enable or disable the extension")