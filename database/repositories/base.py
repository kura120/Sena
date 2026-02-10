# src/database/repositories/base.py
"""Base repository class."""

from typing import Any, Generic, Optional, TypeVar, Protocol, runtime_checkable

from src.database.connection import DatabaseManager


@runtime_checkable
class DatabaseModel(Protocol):
    """Protocol for database models."""
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database insertion."""
        ...
    
    @classmethod
    def from_row(cls, row: Any) -> "DatabaseModel":
        """Create from database row."""
        ...


T = TypeVar("T", bound=DatabaseModel)


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.
    
    Type parameter T is the model class.
    """
    
    def __init__(self, db: DatabaseManager, table_name: str, model_class: type[T]):
        self.db = db
        self.table_name = table_name
        self.model_class = model_class
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get a record by ID."""
        row = await self.db.fetch_one(
            f"SELECT * FROM {self.table_name} WHERE id = ?",
            (id,)
        )
        if row is None:
            return None
        return self.model_class.from_row(row)  # type: ignore
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Get all records with pagination."""
        rows = await self.db.fetch_all(
            f"SELECT * FROM {self.table_name} ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [self.model_class.from_row(row) for row in rows]  # type: ignore
    
    async def create(self, model: T) -> int:
        """Create a new record."""
        return await self.db.insert(self.table_name, model.to_db_dict())
    
    async def update(self, id: int, data: dict[str, Any]) -> int:
        """Update a record."""
        return await self.db.update(self.table_name, data, "id = ?", (id,))
    
    async def delete(self, id: int) -> int:
        """Delete a record."""
        return await self.db.delete(self.table_name, "id = ?", (id,))
    
    async def count(self) -> int:
        """Count all records."""
        row = await self.db.fetch_one(f"SELECT COUNT(*) as count FROM {self.table_name}")
        return row["count"] if row else 0