# src/database/repositories/extension_repo.py
"""Extension repository."""

from datetime import datetime
from typing import Optional

from src.database.connection import DatabaseManager
from src.database.models.extension import Extension
from src.database.repositories.base import BaseRepository


class ExtensionRepository(BaseRepository[Extension]):
    """Repository for extension operations."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(db, "extensions", Extension)
    
    async def get_by_name(self, name: str) -> Optional[Extension]:
        """Get an extension by name."""
        row = await self.db.fetch_one(
            "SELECT * FROM extensions WHERE name = ?",
            (name,)
        )
        return Extension.from_row(row) if row else None
    
    async def get_active(self) -> list[Extension]:
        """Get all active extensions."""
        rows = await self.db.fetch_all(
            "SELECT * FROM extensions WHERE status = 'active' ORDER BY name"
        )
        return [Extension.from_row(row) for row in rows]
    
    async def get_by_type(self, extension_type: str) -> list[Extension]:
        """Get extensions by type."""
        rows = await self.db.fetch_all(
            "SELECT * FROM extensions WHERE extension_type = ? ORDER BY name",
            (extension_type,)
        )
        return [Extension.from_row(row) for row in rows]
    
    async def update_status(self, name: str, status: str) -> bool:
        """Update an extension's status."""
        count = await self.db.update(
            self.table_name,
            {"status": status},
            "name = ?",
            (name,)
        )
        return count > 0
    
    async def record_execution(
        self,
        name: str,
        execution_ms: float,
        success: bool,
    ) -> bool:
        """Record an extension execution."""
        ext = await self.get_by_name(name)
        if not ext:
            return False
        
        # Calculate new average
        total_executions = ext.execution_count + 1
        new_avg = (
            (ext.avg_execution_ms * ext.execution_count + execution_ms)
            / total_executions
        )
        
        updates = {
            "execution_count": total_executions,
            "avg_execution_ms": new_avg,
            "last_loaded": datetime.now().isoformat(),
        }
        
        if not success:
            updates["error_count"] = ext.error_count + 1
        
        count = await self.db.update(
            self.table_name,
            updates,
            "name = ?",
            (name,)
        )
        return count > 0
    
    async def upsert(self, extension: Extension) -> Optional[int]:
        """Insert or update an extension."""
        existing = await self.get_by_name(extension.name)
        
        if existing:
            await self.db.update(
                self.table_name,
                extension.to_db_dict(),
                "name = ?",
                (extension.name,)
            )
            return existing.id
        else:
            return await self.create(extension)