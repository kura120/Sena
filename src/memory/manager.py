"""Main memory orchestrator coordinating all memory systems."""

from typing import Any, Optional

from src.api.websocket.manager import ws_manager
from src.database.connection import DatabaseManager
from src.memory.embeddings import EmbeddingsHandler
from src.memory.long_term import LongTermMemory
from src.memory.mem0_client import Mem0Client
from src.memory.retrieval import RetrievalEngine
from src.memory.short_term import ShortTermMemory
from src.utils.logger import logger


class MemoryManager:
    """Orchestrate short-term and long-term memory with dynamic retrieval.

    This is the main interface for all memory operations.
    """

    _instance: Optional["MemoryManager"] = None

    def __init__(
        self,
        db_connection: Optional[DatabaseManager] = None,
        mem0_api_key: Optional[str] = None,
        mem0_base_url: Optional[str] = None,
        mem0_mode: str = "library",
        mem0_llm_model: Optional[str] = None,
        mem0_embed_model: Optional[str] = None,
        mem0_ollama_base_url: Optional[str] = None,
        short_term_max_messages: int = 20,
        short_term_ttl_hours: int = 1,
    ):
        """Initialize memory manager.

        Args:
            db_connection: Database manager instance
            mem0_api_key: mem0 API key (for cloud mode)
            mem0_base_url: mem0 base URL (for self-hosted)
            mem0_mode: "cloud" or "self_hosted"
        """
        self.db = db_connection

        # Initialize all memory components
        self.embeddings = EmbeddingsHandler()
        self.short_term = ShortTermMemory(
            max_messages=short_term_max_messages,
            ttl_hours=short_term_ttl_hours,
        )
        self.long_term = LongTermMemory(db_connection=db_connection)
        self.mem0_client = Mem0Client(
            api_key=mem0_api_key,
            base_url=mem0_base_url,
            mode=mem0_mode,
            mem0_llm_model=mem0_llm_model,
            mem0_embed_model=mem0_embed_model,
            mem0_ollama_base_url=mem0_ollama_base_url,
        )
        self.retrieval_engine = RetrievalEngine(
            short_term=self.short_term, long_term=self.long_term, embeddings=self.embeddings
        )

        self.initialized = False
        logger.info("MemoryManager initialized")

    @classmethod
    def get_instance(cls) -> "MemoryManager":
        """Get singleton instance of MemoryManager.

        Returns:
            MemoryManager instance
        """
        if cls._instance is None:
            from src.config.settings import get_settings

            settings = get_settings()
            cls._instance = cls(
                mem0_api_key=settings.memory.mem0.api_key,
                mem0_base_url=settings.memory.mem0.base_url,
                mem0_mode=settings.memory.mem0.mode,
                mem0_llm_model=settings.llm.models["fast"].name,
                mem0_embed_model=settings.memory.embeddings.model,
                mem0_ollama_base_url=settings.llm.base_url,
                short_term_max_messages=settings.memory.short_term.max_messages,
                short_term_ttl_hours=max(1, int(settings.memory.short_term.expire_after / 3600)),
            )
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "MemoryManager") -> None:
        """Set singleton instance.

        Args:
            instance: MemoryManager instance to use
        """
        cls._instance = instance

    async def initialize(self) -> bool:
        """Initialize all memory systems.

        Returns:
            True if all systems initialized successfully
        """
        try:
            logger.info("Initializing memory systems...")

            if not self.db:
                from src.database.connection import get_db

                self.db = await get_db()
                self.long_term.db = self.db

            # Check mem0 connection
            mem0_connected = await self.mem0_client.check_connection()
            if not mem0_connected:
                logger.warning("mem0 not available, using local storage only")

            # Initialize database tables if needed
            if self.db:
                await self.db.initialize()
                logger.info("Database initialized for memory storage")

            self.initialized = True
            logger.info("Memory systems initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing memory systems: {e}")
            self.initialized = False
            return False

    # Short-term memory operations
    async def add_to_context(self, content: str, role: str = "user", metadata: Optional[dict] = None) -> Any:
        """Add message to short-term context buffer.

        Args:
            content: Message content
            role: "user", "assistant", or "system"
            metadata: Optional metadata

        Returns:
            Added MemoryItem
        """
        try:
            return await self.short_term.add(content=content, role=role, metadata=metadata)
        except Exception as e:
            logger.error(f"Error adding to short-term context: {e}")
            raise

    async def get_conversation_context(self, limit: Optional[int] = None) -> str:
        """Get formatted conversation context for LLM.

        Args:
            limit: Max messages to include

        Returns:
            Formatted context string
        """
        try:
            return await self.short_term.get_context(limit=limit)
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""

    async def clear_context(self) -> int:
        """Clear short-term context buffer.

        Returns:
            Number of items cleared
        """
        try:
            return await self.short_term.clear()
        except Exception as e:
            logger.error(f"Error clearing context: {e}")
            return 0

    # Long-term memory operations
    async def remember(self, content: str, metadata: Optional[dict] = None) -> dict[str, Any]:
        """Store learning/memory in long-term storage.

        Args:
            content: Memory content
            metadata: Optional metadata

        Returns:
            Storage result
        """
        try:
            # Generate embedding
            embedding = await self.embeddings.generate_embedding(content)

            # Store in database
            result = await self.long_term.add(content=content, metadata=metadata, embedding=embedding)

            try:
                await ws_manager.broadcast_memory_update(
                    action="stored",
                    memory_id=str(result.get("memory_id")) if result.get("memory_id") is not None else None,
                    details={"content": content, "metadata": metadata or {}},
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast memory update: {e}")

            # Also try to store in mem0 if available
            if self.mem0_client.connected:
                await self.mem0_client.add_memory(content=content, metadata=metadata)

            return result

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise

    async def recall(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search long-term memory.

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of matching memories
        """
        try:
            return await self.long_term.search(query=query, k=k)
        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return []

    async def recent_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent long-term memories."""
        try:
            return await self.long_term.recent(limit=limit)
        except Exception as e:
            logger.error(f"Error retrieving recent memories: {e}")
            return []

    # Dynamic retrieval operations
    async def should_use_memory(self, user_input: str, intent_type: Optional[str] = None) -> bool:
        """Determine if memory should be retrieved for this input.

        Args:
            user_input: User's input
            intent_type: Classified intent

        Returns:
            True if memory should be used
        """
        try:
            return await self.retrieval_engine.should_retrieve(user_input=user_input, intent_type=intent_type)
        except Exception as e:
            logger.error(f"Error in should_use_memory: {e}")
            return False

    async def get_relevant_memories(self, user_input: str, k: int = 5) -> dict[str, Any]:
        """Get memories relevant to user input.

        Args:
            user_input: User's input
            k: Number of long-term results

        Returns:
            Dictionary with short and long-term memories
        """
        try:
            return await self.retrieval_engine.retrieve_relevant(user_input=user_input, k=k)
        except Exception as e:
            logger.error(f"Error retrieving relevant memories: {e}")
            return {"short_term": [], "long_term": []}

    async def build_llm_context(self, user_input: str, intent_type: Optional[str] = None) -> str:
        """Build complete context for LLM processing.

        Args:
            user_input: User's input
            intent_type: Classified intent

        Returns:
            Formatted context string
        """
        try:
            return await self.retrieval_engine.get_context_for_llm(
                user_input=user_input, intent_type=intent_type, include_memories=True
            )
        except Exception as e:
            logger.error(f"Error building LLM context: {e}")
            return ""

    # Learning extraction and storage
    async def extract_and_store_learnings(
        self, conversation: str, metadata: Optional[dict] = None
    ) -> list[dict[str, Any]]:
        """Extract learnings from conversation and store them.

        Args:
            conversation: Full conversation text
            metadata: Optional metadata

        Returns:
            List of stored learnings
        """
        try:
            # Extract learnings from conversation
            learnings = await self.retrieval_engine.extract_learnings(conversation=conversation)

            if not learnings:
                logger.debug("No learnings extracted from conversation")
                return []

            # Add metadata to each learning
            learning_metadata = metadata or {}
            learning_metadata["source"] = "conversation_extraction"

            # Store learnings
            results = await self.retrieval_engine.store_learnings(learnings=learnings, metadata=learning_metadata)

            return results

        except Exception as e:
            logger.error(f"Error extracting and storing learnings: {e}")
            return []

    # Statistics and diagnostics
    async def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about all memory systems.

        Returns:
            Dictionary with memory statistics
        """
        try:
            return {
                "short_term": self.short_term.get_stats(),
                "long_term": await self.long_term.get_stats(),
                "mem0_connected": self.mem0_client.connected,
                "initialized": self.initialized,
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}

    async def get_retrieval_stats(self) -> dict[str, Any]:
        """Get retrieval engine statistics.

        Returns:
            Retrieval statistics
        """
        try:
            return await self.retrieval_engine.get_retrieval_stats()
        except Exception as e:
            logger.error(f"Error getting retrieval stats: {e}")
            return {}

    # Memory management
    async def forget_memory(self, memory_id: int) -> bool:
        """Delete specific memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful
        """
        try:
            return await self.long_term.delete(memory_id)
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    async def clear_all_memories(self) -> bool:
        """Clear all memories (use with caution!).

        Returns:
            True if successful
        """
        try:
            # Clear short-term
            await self.short_term.clear()

            # Clear mem0 if available
            if self.mem0_client.connected:
                await self.mem0_client.clear_all_memories()

            logger.warning("Cleared all memories")
            return True

        except Exception as e:
            logger.error(f"Error clearing all memories: {e}")
            return False

    async def shutdown(self) -> None:
        """Gracefully shutdown memory systems."""
        try:
            logger.info("Shutting down memory systems...")

            # Close mem0 client
            await self.mem0_client.close()

            self.initialized = False
            logger.info("Memory systems shutdown complete")

        except Exception as e:
            logger.error(f"Error during memory shutdown: {e}")
