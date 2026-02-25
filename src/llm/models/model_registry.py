# src/llm/models/model_registry.py
"""
Model Registry for Runtime Model Switching

Manages multiple LLM models and enables switching between them.

Router model is always interlocked to the fast model at initialization time.
There is no separate router configuration — the same OllamaClient instance
is shared, so classification and generation never cause a VRAM model swap.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from src.config.settings import LLMModelConfig, get_settings
from src.core.constants import ModelType
from src.core.exceptions import LLMModelNotFoundError
from src.llm.models.base import BaseLLM
from src.llm.models.ollama_client import OllamaClient
from src.utils.logger import logger


class ModelInfo:
    """Information about a registered model."""

    def __init__(
        self,
        model_type: ModelType,
        config: LLMModelConfig,
        client: BaseLLM,
    ):
        self.model_type = model_type
        self.config = config
        self.client = client
        self.last_used: Optional[datetime] = None
        self.use_count: int = 0
        self.total_tokens: int = 0
        self.total_duration_ms: float = 0.0

    def record_usage(self, tokens: int, duration_ms: float) -> None:
        """Record usage statistics."""
        self.last_used = datetime.now()
        self.use_count += 1
        self.total_tokens += tokens
        self.total_duration_ms += duration_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_type": self.model_type.value,
            "model_name": self.config.name,
            "is_loaded": self.client.is_loaded,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "total_tokens": self.total_tokens,
            "avg_duration_ms": self.total_duration_ms / self.use_count if self.use_count > 0 else 0,
        }


class ModelRegistry:
    """
    Registry for managing multiple LLM models.

    Provides:
    - Model registration and initialization
    - Runtime model switching
    - Per-model locking for safe concurrent access
    - Usage tracking and statistics

    The router model is always interlocked to the fast model — they share
    the same OllamaClient instance so there is never a VRAM swap between
    intent classification and response generation.
    """

    def __init__(self):
        self._models: dict[ModelType, ModelInfo] = {}
        self._active_model: Optional[ModelType] = None
        self._switch_lock = asyncio.Lock()
        self._model_locks: dict[ModelType, asyncio.Lock] = {}
        self._last_switch: Optional[datetime] = None
        self._settings = get_settings()

    async def initialize(self) -> None:
        """Initialize all configured models and interlock router to fast."""
        logger.info("Initializing model registry...")

        settings = self._settings.llm

        # Register each explicitly configured model type.
        # ROUTER is intentionally excluded here — it is always interlocked
        # to FAST below and must never get its own separate OllamaClient.
        for model_type in ModelType:
            if model_type == ModelType.ROUTER:
                continue
            if model_type.value in settings.models:
                config = settings.models[model_type.value]
                await self.register_model(model_type, config)

        # Load the fast model by default so it is warm for the first request.
        if ModelType.FAST in self._models:
            await self.switch_to(ModelType.FAST)

        # Hard-interlock: router always shares the fast model's ModelInfo.
        # Same OllamaClient instance → same already-loaded model in Ollama →
        # zero VRAM swap between classification and generation.
        if ModelType.FAST in self._models:
            fast_info = self._models[ModelType.FAST]
            self._models[ModelType.ROUTER] = fast_info
            # Share the same per-model lock so concurrent callers deduplicate
            # correctly regardless of whether they ask for FAST or ROUTER.
            self._model_locks[ModelType.ROUTER] = self._model_locks[ModelType.FAST]
            logger.info(
                f"Router interlocked to fast model ({fast_info.config.name}) — no separate router model or VRAM swap."
            )
        else:
            logger.warning("Fast model not registered — router interlock skipped.")

        logger.info(
            f"Model registry initialized with {len({id(v) for v in self._models.values()})} unique model(s) "
            f"across {len(self._models)} slot(s)"
        )

    async def register_model(
        self,
        model_type: ModelType,
        config: LLMModelConfig,
    ) -> None:
        """
        Register a model with the registry.

        Args:
            model_type: Type of model (fast, critical, code)
            config: Model configuration
        """
        settings = self._settings.llm

        client = OllamaClient(
            model_name=config.name,
            base_url=settings.base_url,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            context_window=config.context_window,
            timeout=settings.timeout,
            keep_alive=str(self._settings.llm.ollama_keep_alive),
        )

        self._models[model_type] = ModelInfo(
            model_type=model_type,
            config=config,
            client=client,
        )

        # Each model type gets its own asyncio.Lock so concurrent callers for
        # *different* models never block each other.
        self._model_locks[model_type] = asyncio.Lock()

        logger.debug(f"Registered model: {model_type.value} -> {config.name}")

    async def get_client(self, model_type: ModelType) -> BaseLLM:
        """
        Return the client for a model type, loading it if necessary.

        Uses a per-model asyncio.Lock so:
        - Concurrent callers for the *same* model deduplicate the load
          (only one load() call is made, others wait and reuse the result).
        - Callers for *different* models never block each other.

        Does NOT update _active_model — use switch_to() for that.

        Args:
            model_type: Type of model to get

        Returns:
            The model's BaseLLM client, guaranteed loaded.

        Raises:
            LLMModelNotFoundError: If model_type is not registered.
        """
        if model_type not in self._models:
            raise LLMModelNotFoundError(model_type.value)

        model_info = self._models[model_type]
        lock = self._model_locks.get(model_type, self._switch_lock)

        async with lock:
            if not model_info.client.is_loaded:
                logger.info(f"Loading model: {model_type.value} ({model_info.config.name})")
                await model_info.client.load()

        return model_info.client

    async def switch_to(self, model_type: ModelType, force: bool = False) -> BaseLLM:
        """
        Switch to a different model, updating the active model pointer.

        Args:
            model_type: Type of model to switch to
            force: Unused, kept for API compatibility

        Returns:
            The switched-to model client
        """
        async with self._switch_lock:
            if model_type not in self._models:
                raise LLMModelNotFoundError(model_type.value)

            model_info = self._models[model_type]

            if not model_info.client.is_loaded:
                logger.info(f"Loading model: {model_type.value} ({model_info.config.name})")
                await model_info.client.load()

            self._active_model = model_type
            self._last_switch = datetime.now()

            logger.debug(f"Switched to model: {model_type.value} ({model_info.config.name})")

            return model_info.client

    def get_model(self, model_type: ModelType) -> Optional[BaseLLM]:
        """
        Get a model client by type without switching or loading.

        Args:
            model_type: Type of model to get

        Returns:
            Model client if registered, None otherwise
        """
        if model_type in self._models:
            return self._models[model_type].client
        return None

    def get_active_model(self) -> Optional[BaseLLM]:
        """Get the currently active model."""
        if self._active_model and self._active_model in self._models:
            return self._models[self._active_model].client
        return None

    def get_active_model_type(self) -> Optional[ModelType]:
        """Get the type of the currently active model."""
        return self._active_model

    def record_usage(
        self,
        model_type: ModelType,
        tokens: int,
        duration_ms: float,
    ) -> None:
        """Record usage statistics for a model."""
        if model_type in self._models:
            self._models[model_type].record_usage(tokens, duration_ms)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics for all models."""
        return {
            "active_model": self._active_model.value if self._active_model else None,
            "models": {model_type.value: info.to_dict() for model_type, info in self._models.items()},
            "last_switch": self._last_switch.isoformat() if self._last_switch else None,
        }

    async def health_check(self) -> dict[str, bool]:
        """Check health of all registered models."""
        seen: set[int] = set()
        results = {}
        for model_type, info in self._models.items():
            client_id = id(info.client)
            if client_id in seen:
                # Interlocked slot — reuse result from the primary slot
                primary = next(mt for mt, mi in self._models.items() if id(mi.client) == client_id and mt != model_type)
                results[model_type.value] = results.get(primary.value, False)
                continue
            seen.add(client_id)
            try:
                results[model_type.value] = await info.client.health_check()
            except Exception:
                results[model_type.value] = False
        return results

    async def shutdown(self) -> None:
        """Shutdown all models, deduplicating shared clients."""
        logger.info("Shutting down model registry...")

        seen: set[int] = set()
        for model_type, info in self._models.items():
            client_id = id(info.client)
            if client_id in seen:
                continue  # Already shut down via shared reference
            seen.add(client_id)
            if info.client.is_loaded:
                try:
                    await info.client.unload()
                except Exception as e:
                    logger.warning(f"Error unloading {model_type.value}: {e}")

        self._models.clear()
        self._model_locks.clear()
        self._active_model = None

        logger.info("Model registry shutdown complete")
