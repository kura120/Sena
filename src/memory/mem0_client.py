"""mem0 API client for AI-powered memory management."""

import builtins
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import httpx
from loguru import logger

try:
    from mem0 import Memory
except Exception:  # pragma: no cover - optional dependency
    Memory = Any


class Mem0Client:
    """Integration with mem0 for AI-powered memory.

    Supports both:
    - Cloud API (mem0.com)
    - Self-hosted instance
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mode: str = "library",
        mem0_llm_model: Optional[str] = None,
        mem0_embed_model: Optional[str] = None,
        mem0_ollama_base_url: Optional[str] = None,
    ):
        """Initialize mem0 client.

        Args:
            api_key: API key for mem0 (cloud mode)
            base_url: Base URL for self-hosted instance
            mode: "cloud" or "self_hosted"
        """
        self.api_key = api_key
        self.mode = mode
        self.mem0_llm_model = mem0_llm_model or "llama3.1"
        self.mem0_embed_model = mem0_embed_model or "nomic-embed-text"
        self.mem0_ollama_base_url = mem0_ollama_base_url or "http://localhost:11434"
        self._local_memory: Optional[Any] = None

        if mode == "self_hosted":
            self.base_url = base_url or "http://localhost:6333"
        else:
            self.base_url = "https://api.mem0.ai/v1"

        self.client: Optional[httpx.AsyncClient] = None
        if self.mode != "library":
            self.client = httpx.AsyncClient(headers=self._get_headers(), timeout=30.0)
        self.connected = False

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Dictionary of headers
        """
        headers = {"Content-Type": "application/json"}

        if self.api_key and self.mode == "cloud":
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    @staticmethod
    def _is_dimension_mismatch(exc: Exception) -> bool:
        """Return True when *exc* is a numpy/ChromaDB embedding shape error."""
        msg = str(exc).lower()
        return "not aligned" in msg or ("shapes" in msg and "dim" in msg)

    def _get_mem0_storage_path(self) -> Path:
        """Return the default mem0 local storage directory."""
        return Path.home() / ".mem0"

    def _reset_local_memory(self) -> None:
        """
        Wipe mem0's local ChromaDB storage and mark the client as
        uninitialised.  Called when an embedding dimension mismatch is
        detected so the collection is re-created with the correct dimensions
        on the next add/search call.
        """
        storage = self._get_mem0_storage_path()
        if storage.exists():
            logger.warning(
                f"Embedding dimension mismatch — resetting mem0 storage at "
                f"{storage}.  All previously stored mem0 vectors will be "
                f"re-indexed on the next memory operation."
            )
            shutil.rmtree(storage, ignore_errors=True)
        self._local_memory = None
        self.connected = False

    def _ensure_local_memory(self) -> bool:
        if self._local_memory is not None:
            return True
        if Memory is Any:
            logger.error("mem0ai is not installed; cannot use library mode")
            return False
        try:
            import ollama  # noqa: F401
        except Exception as e:
            logger.error(f"ollama Python client is missing: {e}")
            return False
        try:
            try:
                httpx.get(f"{self.mem0_ollama_base_url}/api/tags", timeout=1.5)
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Ollama at {self.mem0_ollama_base_url}: {e}") from e
            config = {
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": self.mem0_llm_model,
                        "temperature": 0,
                    },
                },
                "embedder": {
                    "provider": "ollama",
                    "config": {
                        "model": self.mem0_embed_model,
                    },
                },
                "version": "v1.1",
            }
            original_input = builtins.input
            try:
                builtins.input = lambda *_args, **_kwargs: "n"
                self._local_memory = cast(Any, Memory).from_config(config)
            finally:
                builtins.input = original_input
            return True
        except Exception as e:
            logger.error(f"Error initializing mem0 library client: {e}")
            return False

    async def check_connection(self) -> bool:
        """Check if mem0 instance is accessible.

        Returns:
            True if connected, False otherwise
        """
        try:
            if self.mode == "library":
                self.connected = self._ensure_local_memory()
                logger.info(f"mem0 library connection check: {self.connected}")
                return self.connected
            if self.mode == "self_hosted":
                # Check Qdrant health
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health")
                    self.connected = response.status_code == 200
            else:
                # Check cloud API
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health", headers=self._get_headers())
                    self.connected = response.status_code == 200

            logger.info(f"mem0 connection check: {self.connected}")
            return self.connected

        except Exception as e:
            logger.error(f"Error checking mem0 connection: {e}")
            self.connected = False
            return False

    async def add_memory(self, content: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        """Add memory to mem0.

        Args:
            content: Memory content
            metadata: Optional metadata tags

        Returns:
            Response from mem0 API
        """
        try:
            if self.mode == "library":
                if not self.connected:
                    logger.warning("mem0 not connected, skipping add_memory")
                    return {"status": "error", "message": "Not connected to mem0"}
                if self._local_memory is None:
                    return {"status": "error", "message": "mem0 library not initialized"}
                user_id = (metadata or {}).get("session_id", "default")
                try:
                    try:
                        result = self._local_memory.add(content, user_id=user_id, metadata=metadata or {})
                    except TypeError:
                        result = self._local_memory.add(content, user_id=user_id)
                    logger.debug(f"Added memory to mem0 (library): {result}")
                    return result if isinstance(result, dict) else {"status": "ok", "result": result}
                except Exception as inner_exc:
                    if self._is_dimension_mismatch(inner_exc):
                        logger.warning(
                            "mem0 add_memory: dimension mismatch detected — resetting storage and retrying once."
                        )
                        self._reset_local_memory()
                        if not self._ensure_local_memory():
                            return {"status": "error", "message": "Failed to reinitialise mem0 after reset"}
                        try:
                            result = self._local_memory.add(content, user_id=user_id, metadata=metadata or {})
                        except TypeError:
                            result = self._local_memory.add(content, user_id=user_id)
                        return result if isinstance(result, dict) else {"status": "ok", "result": result}
                    raise
            if not self.client:
                return {"status": "error", "message": "mem0 client not initialized"}
            if not self.connected:
                logger.warning("mem0 not connected, skipping add_memory")
                return {"status": "error", "message": "Not connected to mem0"}

            payload = {"messages": [{"role": "user", "content": content}], "metadata": metadata or {}}

            response = await self.client.post(f"{self.base_url}/memories/add", json=payload)

            result = response.json()
            logger.debug(f"Added memory to mem0: {result}")
            return result

        except Exception as e:
            logger.error(f"Error adding memory to mem0: {e}")
            return {"status": "error", "message": str(e)}

    async def search_memories(
        self, query: str, k: int = 5, metadata_filter: Optional[dict] = None
    ) -> list[dict[str, Any]]:
        """Search memories in mem0.

        Args:
            query: Search query
            k: Number of results
            metadata_filter: Optional metadata filter

        Returns:
            List of matching memories
        """
        try:
            if self.mode == "library":
                if not self.connected:
                    logger.warning("mem0 not connected, skipping search")
                    return []
                if self._local_memory is None:
                    return []
                user_id = (metadata_filter or {}).get("session_id", "default")
                try:
                    try:
                        results = self._local_memory.search(query, user_id=user_id, limit=k)
                    except TypeError:
                        results = self._local_memory.search(query, user_id=user_id)
                    logger.debug(f"Found {len(results)} memories in mem0 (library)")
                    return results if isinstance(results, list) else []
                except Exception as inner_exc:
                    if self._is_dimension_mismatch(inner_exc):
                        logger.warning(
                            "mem0 search_memories: dimension mismatch detected — "
                            "resetting storage (returning empty results this call)."
                        )
                        self._reset_local_memory()
                        # Don't retry search — no valid vectors exist after reset.
                        return []
                    raise
            if not self.client:
                return []
            if not self.connected:
                logger.warning("mem0 not connected, skipping search")
                return []

            payload = {"query": query, "limit": k, "metadata_filter": metadata_filter or {}}

            response = await self.client.post(f"{self.base_url}/memories/search", json=payload)

            results = response.json()
            logger.debug(f"Found {len(results)} memories in mem0")
            return results

        except Exception as e:
            logger.error(f"Error searching memories in mem0: {e}")
            return []

    async def update_memory(self, memory_id: str, content: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        """Update existing memory in mem0.

        Args:
            memory_id: ID of memory to update
            content: Updated content
            metadata: Updated metadata

        Returns:
            Response from mem0 API
        """
        try:
            if self.mode == "library":
                logger.warning("mem0 library update is not supported")
                return {"status": "error", "message": "Update not supported in library mode"}
            if not self.client:
                return {"status": "error", "message": "mem0 client not initialized"}
            if not self.connected:
                logger.warning("mem0 not connected, skipping update")
                return {"status": "error", "message": "Not connected to mem0"}

            payload = {"id": memory_id, "messages": [{"role": "user", "content": content}], "metadata": metadata or {}}

            response = await self.client.put(f"{self.base_url}/memories/{memory_id}", json=payload)

            result = response.json()
            logger.debug(f"Updated memory in mem0: {memory_id}")
            return result

        except Exception as e:
            logger.error(f"Error updating memory in mem0: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from mem0.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful
        """
        try:
            if self.mode == "library":
                logger.warning("mem0 library delete is not supported")
                return False
            if not self.client:
                return False
            if not self.connected:
                logger.warning("mem0 not connected, skipping delete")
                return False

            response = await self.client.delete(f"{self.base_url}/memories/{memory_id}")

            logger.info(f"Deleted memory from mem0: {memory_id}")
            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error deleting memory from mem0: {e}")
            return False

    async def get_memories_by_tag(self, tag: str, k: int = 10) -> list[dict[str, Any]]:
        """Get memories with specific tag.

        Args:
            tag: Tag to search for
            k: Maximum results

        Returns:
            List of memories with tag
        """
        try:
            if self.mode == "library":
                logger.warning("mem0 library tag search is not supported")
                return []
            if not self.client:
                return []
            if not self.connected:
                return []

            payload = {"metadata_filter": {"tags": tag}, "limit": k}

            response = await self.client.post(f"{self.base_url}/memories/search", json=payload)

            return response.json()

        except Exception as e:
            logger.error(f"Error getting memories by tag: {e}")
            return []

    async def clear_all_memories(self) -> bool:
        """Clear all memories from mem0 (use with caution!).

        Returns:
            True if successful
        """
        try:
            if self.mode == "library":
                if not self.connected:
                    return False
                if self._local_memory is None:
                    return False
                if hasattr(self._local_memory, "reset"):
                    self._local_memory.reset()
                    logger.warning("Cleared all memories from mem0 (library)")
                    return True
                if hasattr(self._local_memory, "clear"):
                    self._local_memory.clear()
                    logger.warning("Cleared all memories from mem0 (library)")
                    return True
                logger.warning("mem0 library clear is not supported")
                return False
            if not self.client:
                return False
            if not self.connected:
                return False

            response = await self.client.delete(f"{self.base_url}/memories")

            logger.warning("Cleared all memories from mem0")
            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error clearing memories: {e}")
            return False

    async def close(self) -> None:
        """Close client connection."""
        try:
            if self.client:
                await self.client.aclose()
                logger.debug("Closed mem0 client")
        except Exception as e:
            logger.error(f"Error closing mem0 client: {e}")
