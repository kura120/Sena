"""Short-term memory buffer for conversation context."""

from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel

from src.utils.logger import logger


class MemoryItem(BaseModel):
    """Single memory item in short-term buffer."""

    id: str
    content: str
    role: str  # "user", "assistant", "system"
    timestamp: datetime
    metadata: dict = {}
    expires_at: Optional[datetime] = None


class ShortTermMemory:
    """Session buffer for recent conversation context.

    - Configurable max messages per session
    - Configurable expiration window
    - FIFO eviction when limit reached
    """

    def __init__(self, max_messages: int = 20, ttl_hours: int = 1):
        """Initialize short-term memory.

        Args:
            max_messages: Maximum messages to keep (FIFO eviction)
            ttl_hours: Time-to-live in hours
        """
        self.max_messages = max_messages
        self.ttl_hours = ttl_hours
        self.buffer: list[MemoryItem] = []

    async def add(self, content: str, role: str, metadata: Optional[dict] = None) -> MemoryItem:
        """Add message to short-term buffer.

        Args:
            content: Message content
            role: "user", "assistant", or "system"
            metadata: Optional metadata dict

        Returns:
            The added MemoryItem
        """
        try:
            now = datetime.now()
            expires_at = now + timedelta(hours=self.ttl_hours)

            item = MemoryItem(
                id=f"short_{len(self.buffer)}_{now.timestamp()}",
                content=content,
                role=role,
                timestamp=now,
                metadata=metadata or {},
                expires_at=expires_at,
            )

            self.buffer.append(item)

            # Remove expired items
            await self._cleanup_expired()

            # Enforce max messages (FIFO)
            if len(self.buffer) > self.max_messages:
                removed = self.buffer.pop(0)
                logger.debug(f"Evicted short-term memory: {removed.id}")

            logger.debug(f"Added to short-term memory: {item.id}")
            return item

        except Exception as e:
            logger.error(f"Error adding to short-term memory: {e}")
            raise

    async def get_all(self) -> list[MemoryItem]:
        """Get all non-expired items in buffer.

        Returns:
            List of MemoryItems
        """
        await self._cleanup_expired()
        return self.buffer.copy()

    async def get_by_role(self, role: str) -> list[MemoryItem]:
        """Get all items with specific role.

        Args:
            role: "user", "assistant", or "system"

        Returns:
            Filtered list of MemoryItems
        """
        await self._cleanup_expired()
        return [item for item in self.buffer if item.role == role]

    async def get_context(self, limit: Optional[int] = None) -> str:
        """Get formatted context string of recent messages.

        Args:
            limit: Max messages to include (None = all)

        Returns:
            Formatted conversation context
        """
        items = await self.get_all()

        if limit:
            items = items[-limit:]

        context_lines = []
        for item in items:
            role_str = item.role.upper()
            context_lines.append(f"{role_str}: {item.content}")

        return "\n".join(context_lines)

    async def clear(self) -> int:
        """Clear all short-term memory.

        Returns:
            Number of items cleared
        """
        count = len(self.buffer)
        self.buffer.clear()
        logger.info(f"Cleared short-term memory ({count} items)")
        return count

    async def _cleanup_expired(self) -> int:
        """Remove expired items from buffer.

        Returns:
            Number of items removed
        """
        now = datetime.now()
        initial_len = len(self.buffer)

        self.buffer = [item for item in self.buffer if item.expires_at is None or item.expires_at > now]

        removed = initial_len - len(self.buffer)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired short-term memories")

        return removed

    def get_stats(self) -> dict:
        """Get statistics about short-term memory.

        Returns:
            Dictionary with stats
        """
        return {
            "total_items": len(self.buffer),
            "user_messages": len([i for i in self.buffer if i.role == "user"]),
            "assistant_messages": len([i for i in self.buffer if i.role == "assistant"]),
            "max_capacity": self.max_messages,
            "usage_percent": (len(self.buffer) / self.max_messages) * 100,
        }
