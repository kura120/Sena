# src/llm/models/base.py
"""
Base LLM Interface

Defines the abstract interface for all LLM implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Optional


class MessageRole(str, Enum):
    """Role of a message in the conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """
    A single message in a conversation.
    
    Attributes:
        role: The role of the message sender
        content: The message content
        timestamp: When the message was created
        metadata: Additional metadata
    """
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for API calls."""
        return {
            "role": self.role.value,
            "content": self.content,
        }
    
    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)


@dataclass
class LLMResponse:
    """
    Response from an LLM.
    
    Attributes:
        content: The generated text content
        model: The model that generated the response
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used
        duration_ms: Generation duration in milliseconds
        finish_reason: Why generation stopped
        metadata: Additional response metadata
    """
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
            },
            "duration_ms": self.duration_ms,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata,
        }


@dataclass
class StreamChunk:
    """
    A chunk from streaming response.
    
    Attributes:
        content: The text content of this chunk
        is_final: Whether this is the final chunk
        metadata: Additional chunk metadata
    """
    content: str
    is_final: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLM(ABC):
    """
    Abstract base class for LLM implementations.
    
    All LLM providers must implement this interface.
    """
    
    def __init__(
        self,
        model_name: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        context_window: int = 8192,
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context_window = context_window
        self._is_loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._is_loaded
    
    @abstractmethod
    async def load(self) -> bool:
        """
        Load and prepare the model.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def unload(self) -> bool:
        """
        Unload the model to free resources.
        
        Returns:
            True if unloaded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
    ) -> LLMResponse:
        """
        Generate a response from the model.
        
        Args:
            messages: Conversation history
            max_tokens: Maximum tokens to generate (overrides default)
            temperature: Sampling temperature (overrides default)
            stop: Stop sequences
            
        Returns:
            LLMResponse with generated content
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream a response from the model.
        
        Args:
            messages: Conversation history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences
            
        Yields:
            StreamChunk objects with content
        """
        # This is intentionally not async def - it returns an AsyncGenerator
        pass
    
    @abstractmethod
    async def get_embeddings(self, text: str) -> list[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the model is healthy and responsive.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.
        
        This is a rough estimate - actual tokenization varies by model.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters for English
        return len(text) // 4
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name}, loaded={self._is_loaded})"