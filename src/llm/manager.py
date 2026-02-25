# src/llm/manager.py
"""
LLM Manager

High-level manager for LLM operations including:
- Model lifecycle management
- Request routing
- Response streaming
- Error handling with recovery
"""

from datetime import datetime
from typing import Any, AsyncIterator, Callable, Coroutine, Optional

from src.config.settings import get_settings
from src.core.constants import ModelType, ProcessingStage
from src.core.exceptions import LLMConnectionError, LLMException, LLMGenerationError
from src.llm.models.base import LLMResponse, Message, StreamChunk
from src.llm.models.model_registry import ModelRegistry
from src.llm.prompts.system_prompts import get_system_prompt
from src.llm.router import IntentResult, IntentRouter
from src.utils.logger import logger


class LLMManager:
    """
    High-level manager for LLM operations.

    Provides:
    - Simplified interface for LLM interactions
    - Automatic model selection based on intent
    - Error handling and recovery
    - Streaming support
    - Usage tracking
    """

    def __init__(self) -> None:
        self._registry = ModelRegistry()
        self._router = IntentRouter()
        self._settings = get_settings()
        self._initialized = False

        # Callbacks for real-time updates
        self._stage_callback: Optional[Callable[[ProcessingStage, str], Coroutine[Any, Any, None]]] = None
        self._token_callback: Optional[Callable[[str, bool], Coroutine[Any, Any, None]]] = None

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """Initialize the LLM manager."""
        if self._initialized:
            return

        logger.info("Initializing LLM manager...")

        # Ensure Ollama is running before attempting any model registry work.
        # This will start Ollama automatically if manage=True and it is not running.
        from src.llm.ollama_manager import get_ollama_manager

        success, message = await get_ollama_manager().ensure_running(self._settings)
        if not success:
            raise LLMConnectionError(f"Cannot connect to Ollama: {message}")

        # Initialize model registry
        await self._registry.initialize()

        # Initialize router
        await self._router.initialize(self._registry)

        self._initialized = True
        logger.info("LLM manager initialized")

    async def shutdown(self) -> None:
        """Shutdown the LLM manager."""
        logger.info("Shutting down LLM manager...")
        await self._registry.shutdown()
        self._initialized = False
        logger.info("LLM manager shutdown complete")

    def set_stage_callback(self, callback: Callable[[ProcessingStage, str], Coroutine[Any, Any, None]]) -> None:
        """Set callback for processing stage updates."""
        self._stage_callback = callback

    def set_token_callback(self, callback: Callable[[str, bool], Coroutine[Any, Any, None]]) -> None:
        """Set callback for streaming tokens."""
        self._token_callback = callback

    async def _notify_stage(self, stage: ProcessingStage, details: str = "") -> None:
        """Notify about processing stage change."""
        if self._stage_callback:
            try:
                await self._stage_callback(stage, details)
            except Exception as e:
                logger.warning(f"Stage callback error: {e}")

    async def _notify_token(self, token: str, is_final: bool = False) -> None:
        """Notify about streamed token."""
        if self._token_callback:
            try:
                await self._token_callback(token, is_final)
            except Exception as e:
                logger.warning(f"Token callback error: {e}")

    async def classify_intent(self, user_input: str) -> IntentResult:
        """
        Classify user intent.

        Args:
            user_input: The user's input message

        Returns:
            IntentResult with classification details
        """
        await self._notify_stage(ProcessingStage.INTENT_CLASSIFICATION, "Analyzing intent...")

        result = await self._router.classify(user_input)

        await self._notify_stage(
            ProcessingStage.INTENT_CLASSIFICATION,
            f"Intent: {result.intent_type.value} (confidence: {result.confidence:.2f})",
        )

        return result

    async def generate(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        context: Optional[list[Message]] = None,
        model_type: Optional[ModelType] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """
        Generate a response for user input.

        Args:
            user_input: The user's input message
            system_prompt: Optional system prompt override
            context: Optional conversation context
            model_type: Force specific model type
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            LLMResponse with generated content
        """
        if not self._initialized:
            raise LLMGenerationError("LLM manager not initialized")

        try:
            # Determine model to use
            if model_type is None:
                intent_result = await self.classify_intent(user_input)
                model_type = intent_result.recommended_model

            # Switch to the appropriate model
            await self._notify_stage(ProcessingStage.LLM_PROCESSING, f"Using {model_type.value} model...")
            model = await self._registry.switch_to(model_type)

            # Build messages
            messages: list[Message] = []

            # Add system prompt
            if system_prompt:
                messages.append(Message.system(system_prompt))
            else:
                messages.append(Message.system(get_system_prompt("default")))

            # Add context messages
            if context:
                messages.extend(context)

            # Add user message
            messages.append(Message.user(user_input))

            # Generate response
            response = await model.generate(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Record usage
            self._registry.record_usage(
                model_type=model_type,
                tokens=response.total_tokens,
                duration_ms=response.duration_ms,
            )

            await self._notify_stage(ProcessingStage.COMPLETE, "Response generated")

            return response

        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise LLMGenerationError(f"Generation failed: {e}")

    async def stream(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        context: Optional[list[Message]] = None,
        model_type: Optional[ModelType] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a response for user input.

        Args:
            user_input: The user's input message
            system_prompt: Optional system prompt override
            context: Optional conversation context
            model_type: Force specific model type
            max_tokens: Override max tokens
            temperature: Override temperature

        Yields:
            StreamChunk objects with content
        """
        if not self._initialized:
            raise LLMGenerationError("LLM manager not initialized")

        # Determine model to use
        if model_type is None:
            intent_result = await self.classify_intent(user_input)
            model_type = intent_result.recommended_model

        # Switch to the appropriate model
        await self._notify_stage(ProcessingStage.LLM_STREAMING, f"Streaming from {model_type.value} model...")
        model = await self._registry.switch_to(model_type)

        # Build messages
        messages: list[Message] = []

        # Add system prompt
        if system_prompt:
            messages.append(Message.system(system_prompt))
        else:
            messages.append(Message.system(get_system_prompt("default")))

        # Add context messages
        if context:
            messages.extend(context)

        # Add user message
        messages.append(Message.user(user_input))

        # Stream response
        total_tokens = 0
        start_time = datetime.now()

        try:
            # model.stream() returns an AsyncGenerator directly, not a coroutine
            stream_gen = model.stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            async for chunk in stream_gen:
                # Notify token callback
                await self._notify_token(chunk.content, chunk.is_final)

                # Track tokens (rough estimate)
                total_tokens += len(chunk.content.split())

                yield chunk

                if chunk.is_final:
                    # Record usage
                    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                    self._registry.record_usage(
                        model_type=model_type,
                        tokens=total_tokens * 2,  # Rough estimate
                        duration_ms=duration_ms,
                    )

                    await self._notify_stage(ProcessingStage.COMPLETE, "Stream complete")

        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            raise LLMGenerationError(f"Streaming failed: {e}")

    async def get_embeddings(
        self,
        text: str,
        model_name: Optional[str] = None,
    ) -> list[float]:
        """
        Generate embeddings for text.

        Args:
            text: Text to embed
            model_name: Specific embedding model to use

        Returns:
            Embedding vector
        """
        # Use configured embedding model
        if model_name is None:
            model_name = self._settings.memory.embeddings.model

        # Create a temporary client for embeddings
        from src.llm.models.ollama_client import OllamaClient

        client = OllamaClient(
            model_name=model_name,
            base_url=self._settings.llm.base_url,
        )

        try:
            return await client.get_embeddings(text)
        finally:
            await client.unload()

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of all LLM components.

        Returns:
            Health status dictionary
        """
        model_health: dict[str, bool] = {}
        if self._initialized:
            model_health = await self._registry.health_check()

        active_type = self._registry.get_active_model_type()

        return {
            "initialized": self._initialized,
            "models": model_health,
            "active_model": active_type.value if active_type else None,
        }

    async def generate_simple(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        model_type: Optional[ModelType] = None,
    ) -> str:
        """
        Generate a response for a single prompt string without conversation context.

        Lightweight wrapper around generate() for internal use cases like personality
        inference and compression where we just need a plain string back.

        Args:
            prompt: The full prompt to send to the LLM.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            model_type: Force a specific model type (defaults to ModelType.FAST).

        Returns:
            Generated text string, or empty string on failure.
        """
        try:
            from src.core.constants import ModelType as MT

            selected_type = model_type or MT.FAST

            if not self._initialized:
                # Try to initialize if not yet done
                try:
                    await self.initialize()
                except Exception as e:
                    logger.warning(f"generate_simple: LLM not initialized: {e}")
                    return ""

            model = await self._registry.switch_to(selected_type)

            messages = [Message.user(prompt)]

            response = await model.generate(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.content if response else ""

        except Exception as e:
            logger.error(f"generate_simple failed: {e}", exc_info=True)
            return ""

    def get_stats(self) -> dict[str, Any]:
        """
        Get LLM usage statistics.

        Returns:
            Statistics dictionary
        """
        return self._registry.get_stats() if self._initialized else {}
