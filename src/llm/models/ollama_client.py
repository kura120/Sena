# src/llm/models/ollama_client.py
"""
Ollama Client Implementation

Provides integration with Ollama for local LLM inference.
"""

import json
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from src.core.exceptions import (
    LLMConnectionError,
    LLMGenerationError,
    LLMModelNotFoundError,
    LLMTimeoutError,
)
from src.llm.models.base import BaseLLM, LLMResponse, Message, StreamChunk
from src.utils.logger import log_llm_call, logger


class OllamaClient(BaseLLM):
    """
    Ollama LLM client implementation.

    Connects to a local or remote Ollama instance for inference.
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        context_window: int = 8192,
        timeout: int = 120,
    ):
        super().__init__(
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            context_window=context_window,
        )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def _close_client(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def load(self) -> bool:
        """
        Load the model by making it warm (ready for inference).

        Ollama loads models on-demand, but we can warm it up.
        """
        try:
            client = await self._get_client()

            # Check if model exists
            response = await client.get("/api/tags")
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if our model is available (with or without tag)
            model_found = any(
                self.model_name in name or name.startswith(self.model_name.split(":")[0]) for name in model_names
            )

            if not model_found:
                logger.warning(f"Model {self.model_name} not found in Ollama")
                raise LLMModelNotFoundError(self.model_name)

            # Warm up the model with a simple request
            logger.info(f"Warming up model {self.model_name}...")

            warm_up_response = await client.post(
                "/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": "Hello",
                    "stream": False,
                    "options": {
                        "num_predict": 1,
                    },
                },
                timeout=float(self.timeout),
            )
            warm_up_response.raise_for_status()

            self._is_loaded = True
            logger.info(f"Model {self.model_name} loaded successfully")
            return True

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.base_url}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout loading model: {e}")
            raise LLMTimeoutError(f"Timeout loading model {self.model_name}")
        except LLMModelNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise LLMGenerationError(f"Failed to load model: {e}")

    async def unload(self) -> bool:
        """Unload the model (close connections)."""
        await self._close_client()
        self._is_loaded = False
        logger.info(f"Model {self.model_name} unloaded")
        return True

    async def generate(
        self,
        messages: list[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
    ) -> LLMResponse:
        """
        Generate a response using Ollama's chat API.
        """
        start_time = time.perf_counter()

        try:
            client = await self._get_client()

            # Build request
            request_body: dict[str, Any] = {
                "model": self.model_name,
                "messages": [m.to_dict() for m in messages],
                "stream": False,
                "options": {
                    "num_predict": max_tokens or self.max_tokens,
                    "temperature": temperature if temperature is not None else self.temperature,
                },
            }

            if stop:
                request_body["options"]["stop"] = stop

            # Make request
            response = await client.post("/api/chat", json=request_body)
            response.raise_for_status()

            data = response.json()

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract token counts
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            # Log the call
            log_llm_call(
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
            )

            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                duration_ms=duration_ms,
                finish_reason=data.get("done_reason", "stop"),
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "eval_duration": data.get("eval_duration"),
                },
            )

        except httpx.ConnectError as e:
            logger.error(f"Connection error during generation: {e}")
            raise LLMConnectionError(f"Failed to connect to Ollama: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during generation: {e}")
            raise LLMTimeoutError(f"Generation timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during generation: {e}")
            raise LLMGenerationError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise LLMGenerationError(f"Generation failed: {e}")

    async def _stream_impl(
        self,
        messages: list[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Internal implementation of streaming.
        """
        try:
            client = await self._get_client()

            # Build request
            request_body: dict[str, Any] = {
                "model": self.model_name,
                "messages": [m.to_dict() for m in messages],
                "stream": True,
                "options": {
                    "num_predict": max_tokens or self.max_tokens,
                    "temperature": temperature if temperature is not None else self.temperature,
                },
            }

            if stop:
                request_body["options"]["stop"] = stop

            # Make streaming request
            async with client.stream("POST", "/api/chat", json=request_body) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        content = data.get("message", {}).get("content", "")
                        is_done = data.get("done", False)

                        if content or is_done:
                            yield StreamChunk(
                                content=content,
                                is_final=is_done,
                                metadata={
                                    "done_reason": data.get("done_reason"),
                                    "eval_count": data.get("eval_count"),
                                }
                                if is_done
                                else {},
                            )
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing stream chunk: {e}")
                        continue

        except httpx.ConnectError as e:
            logger.error(f"Connection error during streaming: {e}")
            raise LLMConnectionError(f"Failed to connect to Ollama: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during streaming: {e}")
            raise LLMTimeoutError(f"Stream timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            raise LLMGenerationError(f"Streaming failed: {e}")

    def stream(
        self,
        messages: list[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream a response using Ollama's chat API.

        Returns an async generator that yields StreamChunk objects.
        """
        return self._stream_impl(messages, max_tokens, temperature, stop)

    async def get_embeddings(self, text: str) -> list[float]:
        """
        Generate embeddings using Ollama's embeddings API.

        Note: Uses nomic-embed-text or similar embedding model.
        """
        try:
            client = await self._get_client()

            response = await client.post(
                "/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text,
                },
            )
            response.raise_for_status()

            data = response.json()
            return data.get("embedding", [])

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise LLMGenerationError(f"Failed to generate embeddings: {e}")

    async def health_check(self) -> bool:
        """Check if Ollama is healthy and responsive."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List all available models in Ollama.

        Returns:
            List of model information dictionaries
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()

            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull (download) a model from Ollama registry.

        Args:
            model_name: Name of the model to pull

        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()

            async with client.stream(
                "POST",
                "/api/pull",
                json={"name": model_name},
                timeout=None,  # No timeout for model download
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        status = data.get("status", "")
                        logger.debug(f"Pull status: {status}")

                        if "error" in data:
                            logger.error(f"Pull error: {data['error']}")
                            return False

            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False

    async def __aenter__(self) -> "OllamaClient":
        """Async context manager entry."""
        await self.load()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.unload()
