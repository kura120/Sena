# src/database/connection.py
"""
Database Connection Manager

Provides async SQLite connection pooling and transaction management.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import aiosqlite

from src.config.settings import get_settings
from src.core.exceptions import DatabaseConnectionError, DatabaseQueryError
from src.utils.logger import logger


class DatabaseManager:
    """
    Manages SQLite database connections with async support.

    Features:
    - Connection pooling
    - Transaction management
    - Auto-migration
    - Thread-safe operations
    """

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = Path(db_path or settings.database.path)
        self.pool_size = settings.database.pool_size
        self.timeout = settings.database.timeout

        self._pool: list[aiosqlite.Connection] = []
        self._pool_lock = asyncio.Lock()
        # Serialises all write operations so concurrent async tasks never
        # race each other for the SQLite write-lock.
        self._write_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database and connection pool."""
        if self._initialized:
            return

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing database at {self.db_path}")

        # Create tables
        await self._create_tables()

        # Run migrations
        await self._run_migrations()

        self._initialized = True
        logger.info("Database initialized successfully")

    async def _create_tables(self) -> None:
        """Create all database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # WAL mode persists in the database file — set it once at init.
            # busy_timeout makes concurrent writers retry instead of failing immediately.
            # synchronous=NORMAL is safe with WAL and much faster than FULL.
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=5000")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.executescript("""
                -- Conversations
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT NOT NULL,
                    sena_response TEXT NOT NULL,
                    model_used TEXT,
                    processing_time_ms REAL,
                    intent_type TEXT,
                    metadata TEXT DEFAULT '{}'
                );

                -- Short-term Memory
                CREATE TABLE IF NOT EXISTS memory_short_term (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Long-term Memory
                CREATE TABLE IF NOT EXISTS memory_long_term (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT,
                    importance INTEGER DEFAULT 5,
                    embedding BLOB,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed DATETIME,
                    metadata TEXT DEFAULT '{}'
                );

                -- Extensions
                CREATE TABLE IF NOT EXISTS extensions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    extension_type TEXT DEFAULT 'user',
                    status TEXT DEFAULT 'active',
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_loaded DATETIME,
                    execution_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    avg_execution_ms REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                -- Telemetry Metrics
                CREATE TABLE IF NOT EXISTS telemetry_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_type TEXT DEFAULT 'gauge',
                    tags TEXT DEFAULT '{}'
                );

                -- Telemetry Errors
                CREATE TABLE IF NOT EXISTS telemetry_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT,
                    stack_trace TEXT,
                    context TEXT DEFAULT '{}',
                    resolved INTEGER DEFAULT 0,
                    resolved_at DATETIME
                );

                -- Logs
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    logger_name TEXT,
                    message TEXT NOT NULL,
                    context TEXT DEFAULT '{}'
                );

                -- Benchmarks
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    component TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT,
                    metadata TEXT DEFAULT '{}'
                );

                -- Schema Version
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
                CREATE INDEX IF NOT EXISTS idx_memory_short_session ON memory_short_term(session_id);
                CREATE INDEX IF NOT EXISTS idx_memory_long_category ON memory_long_term(category);
                CREATE INDEX IF NOT EXISTS idx_memory_long_importance ON memory_long_term(importance);
                CREATE INDEX IF NOT EXISTS idx_extensions_status ON extensions(status);
                CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_telemetry_name ON telemetry_metrics(metric_name);
                CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON telemetry_errors(timestamp);
                CREATE INDEX IF NOT EXISTS idx_errors_type ON telemetry_errors(error_type);
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
                CREATE INDEX IF NOT EXISTS idx_benchmarks_session ON benchmarks(session_id);
                CREATE INDEX IF NOT EXISTS idx_benchmarks_component ON benchmarks(component);
            """)
            await db.commit()

    async def _run_migrations(self) -> None:
        """Run pending database migrations."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current version
            cursor = await db.execute("SELECT MAX(version) FROM schema_version")
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0

            # Apply migrations
            migrations = self._get_migrations()

            for version, migration_sql in migrations.items():
                if version > current_version:
                    logger.info(f"Applying migration v{version}")
                    try:
                        await db.executescript(migration_sql)
                        await db.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                        await db.commit()
                        logger.info(f"Migration v{version} applied successfully")
                    except Exception as e:
                        logger.error(f"Migration v{version} failed: {e}")
                        raise

    def _get_migrations(self) -> dict[int, str]:
        """Get all migrations as version -> SQL mapping."""
        return {
            1: """
                -- Initial schema (already created in _create_tables)
                SELECT 1;
            """,
            2: """
                -- Add full-text search for memories
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content,
                    content_rowid='id'
                );

                -- Trigger to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert
                AFTER INSERT ON memory_long_term BEGIN
                    INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                END;

                CREATE TRIGGER IF NOT EXISTS memory_fts_delete
                AFTER DELETE ON memory_long_term BEGIN
                    DELETE FROM memory_fts WHERE rowid = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS memory_fts_update
                AFTER UPDATE ON memory_long_term BEGIN
                    DELETE FROM memory_fts WHERE rowid = old.id;
                    INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                END;
            """,
            3: """
                -- Personality Fragments
                -- Stores explicit (user-stated) and inferred personality knowledge about Sena's preferences/traits
                CREATE TABLE IF NOT EXISTS personality_fragments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fragment_id TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    fragment_type TEXT NOT NULL DEFAULT 'inferred',
                    category TEXT,
                    confidence REAL DEFAULT 1.0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    source TEXT,
                    version INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    approved_at DATETIME,
                    metadata TEXT DEFAULT '{}'
                );

                -- Personality Audit Log
                -- Tracks all approval/rejection/edit actions on personality fragments
                CREATE TABLE IF NOT EXISTS personality_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fragment_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_content TEXT,
                    new_content TEXT,
                    old_status TEXT,
                    new_status TEXT,
                    confidence REAL,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Indexes for personality tables
                CREATE INDEX IF NOT EXISTS idx_personality_status ON personality_fragments(status);
                CREATE INDEX IF NOT EXISTS idx_personality_type ON personality_fragments(fragment_type);
                CREATE INDEX IF NOT EXISTS idx_personality_category ON personality_fragments(category);
                CREATE INDEX IF NOT EXISTS idx_personality_confidence ON personality_fragments(confidence);
                CREATE INDEX IF NOT EXISTS idx_personality_audit_fragment ON personality_audit(fragment_id);
                CREATE INDEX IF NOT EXISTS idx_personality_audit_timestamp ON personality_audit(timestamp);
            """,
        }

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Get a database connection from the pool.

        Usage:
            async with db.connection() as conn:
                await conn.execute(...)
        """
        conn = None

        try:
            # Try to get from pool
            async with self._pool_lock:
                if self._pool:
                    conn = self._pool.pop()

            # Create new if pool empty
            if conn is None:
                conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=self.timeout,
                )
                conn.row_factory = aiosqlite.Row
                # Apply per-connection settings.  WAL is already set at the
                # database level, but busy_timeout must be set per-connection.
                await conn.execute("PRAGMA busy_timeout=10000")
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")

            yield conn

        finally:
            # Return to pool or close
            if conn:
                async with self._pool_lock:
                    if len(self._pool) < self.pool_size:
                        self._pool.append(conn)
                    else:
                        await conn.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Execute operations within a transaction.

        Usage:
            async with db.transaction() as conn:
                await conn.execute(...)
                await conn.execute(...)
            # Auto-commits on success, rolls back on error
        """
        async with self._write_lock:
            async with self.connection() as conn:
                try:
                    yield conn
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

    async def execute(
        self,
        query: str,
        params: tuple = (),
    ) -> aiosqlite.Cursor:
        """Execute a single query.

        Write statements (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER) are
        serialised through _write_lock and committed immediately so the
        connection never returns to the pool with an open write-lock.
        """
        _write_prefixes = ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE")
        is_write = query.strip().upper().split()[0] in _write_prefixes if query.strip() else False

        if is_write:
            async with self._write_lock:
                async with self.connection() as conn:
                    cursor = await conn.execute(query, params)
                    await conn.commit()
                    return cursor
        else:
            async with self.connection() as conn:
                return await conn.execute(query, params)

    async def execute_many(
        self,
        query: str,
        params_list: list[tuple],
    ) -> None:
        """Execute a query with multiple parameter sets."""
        async with self._write_lock:
            async with self.connection() as conn:
                await conn.executemany(query, params_list)
                await conn.commit()

    async def fetch_one(
        self,
        query: str,
        params: tuple = (),
    ) -> Optional[aiosqlite.Row]:
        """Fetch a single row."""
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            return await cursor.fetchone()

    async def fetch_all(
        self,
        query: str,
        params: tuple = (),
    ) -> list[aiosqlite.Row]:
        """Fetch all rows."""
        async with self.connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return list(rows)  # Convert to list explicitly

    async def insert(
        self,
        table: str,
        data: dict[str, Any],
    ) -> int:
        """
        Insert a row and return the ID.

        Args:
            table: Table name
            data: Column-value mapping

        Returns:
            The inserted row ID
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        values = tuple(data.values())

        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        async with self.transaction() as conn:
            cursor = await conn.execute(query, values)
            lastrowid = cursor.lastrowid
            return lastrowid if lastrowid is not None else 0

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        where: str,
        where_params: tuple = (),
    ) -> int:
        """
        Update rows and return affected count.

        Args:
            table: Table name
            data: Column-value mapping
            where: WHERE clause
            where_params: Parameters for WHERE clause

        Returns:
            Number of affected rows
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        values = tuple(data.values()) + where_params

        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        async with self.transaction() as conn:
            cursor = await conn.execute(query, values)
            return cursor.rowcount

    async def delete(
        self,
        table: str,
        where: str,
        where_params: tuple = (),
    ) -> int:
        """
        Delete rows and return affected count.

        Args:
            table: Table name
            where: WHERE clause
            where_params: Parameters for WHERE clause

        Returns:
            Number of deleted rows
        """
        query = f"DELETE FROM {table} WHERE {where}"

        async with self.transaction() as conn:
            cursor = await conn.execute(query, where_params)
            return cursor.rowcount

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._pool_lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()

        self._initialized = False
        logger.info("Database connections closed")

    async def vacuum(self) -> None:
        """Optimize database by running VACUUM."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("VACUUM")
        logger.info("Database vacuum completed")

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        stats = {}

        tables = [
            "conversations",
            "memory_short_term",
            "memory_long_term",
            "extensions",
            "telemetry_metrics",
            "telemetry_errors",
            "logs",
            "benchmarks",
        ]

        async with self.connection() as conn:
            for table in tables:
                cursor = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                row = await cursor.fetchone()
                stats[table] = row[0] if row else 0

        # Get file size
        if self.db_path.exists():
            stats["file_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

        return stats


# Global database instance
_db_instance: Optional[DatabaseManager] = None


async def get_db() -> DatabaseManager:
    """Get the global database instance."""
    global _db_instance

    if _db_instance is None:
        _db_instance = DatabaseManager()
        await _db_instance.initialize()

    return _db_instance


async def close_db() -> None:
    """Close the global database instance."""
    global _db_instance

    if _db_instance:
        await _db_instance.close()
        _db_instance = None
