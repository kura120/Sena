# src/llm/models/model_registry.py
"""
Model Registry for Runtime Model Switching

Manages multiple LLM models and enables switching between them.
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
    - Usage tracking and statistics
    """

    def __init__(self):
        self._models: dict[ModelType, ModelInfo] = {}
        self._active_model: Optional[ModelType] = None
        self._switch_lock = asyncio.Lock()
        self._last_switch: Optional[datetime] = None
        self._settings = get_settings()

    async def initialize(self) -> None:
        """Initialize all configured models."""
        logger.info("Initializing model registry...")

        settings = self._settings.llm

        # Register each model type
        for model_type in ModelType:
            if model_type.value in settings.models:
                config = settings.models[model_type.value]
                await self.register_model(model_type, config)

        # Load the fast model by default
        if ModelType.FAST in self._models:
            await self.switch_to(ModelType.FAST)

        # Eagerly warm the router model so the first classify() call is not
        # delayed by a full Ollama load. If it shares a name with the fast
        # model the slot is already hot — just mark it loaded to skip the
        # duplicate warm-up round-trip.
        if ModelType.ROUTER in self._models:
            router_info = self._models[ModelType.ROUTER]
            fast_info = self._models.get(ModelType.FAST)
            if fast_info and router_info.config.name == fast_info.config.name:
                router_info.client._is_loaded = True
                logger.info(
                    f"Router model shares name with fast model "
                    f"({router_info.config.name}) — skipping duplicate warm-up."
                )
            else:
                try:
                    logger.info("Pre-loading router model at startup...")
                    await router_info.client.load()
                    logger.info("Router model pre-loaded successfully.")
                except Exception as e:
                    logger.warning(f"Router model pre-load failed (non-fatal): {e}")

        logger.info(f"Model registry initialized with {len(self._models)} models")

    async def register_model(
        self,
        model_type: ModelType,
        config: LLMModelConfig,
    ) -> None:
        """
        Register a model with the registry.

        Args:
            model_type: Type of model (fast, critical, code, router)
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
            keep_alive=self._settings.llm.ollama_keep_alive,
        )

        self._models[model_type] = ModelInfo(
            model_type=model_type,
            config=config,
            client=client,
        )

        logger.debug(f"Registered model: {model_type.value} -> {config.name}")

    async def switch_to(self, model_type: ModelType, force: bool = False) -> BaseLLM:
        """
        Switch to a different model.

        Args:
            model_type: Type of model to switch to
            force: Force switch even if cooldown hasn't passed

        Returns:
            The switched-to model client
        """
        async with self._switch_lock:
            # Check if model exists
            if model_type not in self._models:
                raise LLMModelNotFoundError(model_type.value)

            model_info = self._models[model_type]

            # Load model if not already loaded
            if not model_info.client.is_loaded:
                logger.info(f"Loading model: {model_type.value}")
                await model_info.client.load()

            self._active_model = model_type
            self._last_switch = datetime.now()

            logger.info(f"Switched to model: {model_type.value} ({model_info.config.name})")

            return model_info.client

    def get_model(self, model_type: ModelType) -> Optional[BaseLLM]:
        """
        Get a model by type without switching.

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
        results = {}
        for model_type, info in self._models.items():
            try:
                results[model_type.value] = await info.client.health_check()
            except Exception:
                results[model_type.value] = False
        return results

    async def shutdown(self) -> None:
        """Shutdown all models."""
        logger.info("Shutting down model registry...")

        for model_type, info in self._models.items():
            if info.client.is_loaded:
                try:
                    await info.client.unload()
                except Exception as e:
                    logger.warning(f"Error unloading {model_type.value}: {e}")

        self._models.clear()
        self._active_model = None

        logger.info("Model registry shutdown complete")
