"""Async SQLite connection manager with lifecycle, transactions, and repository access."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import aiosqlite

from wine_crawler.admin.db.schema import apply_migrations

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)


def _row_factory(cursor: aiosqlite.Cursor, row: tuple) -> dict[str, Any]:
    """Convert rows to dicts keyed by column name."""
    columns = [col[0] for col in cursor.description]  # type: ignore[union-attr]
    return dict(zip(columns, row))


class Database:
    """Async SQLite database with lifecycle management.

    Usage::

        db = Database(Path("admin.db"))
        await db.connect()          # opens + runs migrations
        row = await db.fetch_one("SELECT 1")
        await db.disconnect()

    Or as an async context-manager::

        async with Database(Path("admin.db")) as db:
            row = await db.fetch_one("SELECT 1")
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        # Lazy-init: repositories are created after connect()
        self._repos: _RepositoryBundle | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the database, configure pragmas, and apply migrations."""
        if self._conn is not None:
            return

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(self._db_path))

        # Performance & safety pragmas
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA busy_timeout = 5000")
        await conn.execute("PRAGMA synchronous = NORMAL")
        await conn.execute("PRAGMA cache_size = -8000")  # 8 MB

        conn.row_factory = _row_factory  # type: ignore[assignment]
        self._conn = conn

        await apply_migrations(self)
        logger.info("Database connected: %s", self._db_path)

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._conn is None:
            return
        await self._conn.close()
        self._conn = None
        self._repos = None
        logger.info("Database disconnected: %s", self._db_path)

    async def __aenter__(self) -> Database:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Low-level query helpers
    # ------------------------------------------------------------------

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def execute(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> aiosqlite.Cursor:
        """Execute a single SQL statement."""
        cursor = await self.connection.execute(sql, params or [])
        await self.connection.commit()
        return cursor

    async def execute_many(
        self,
        sql: str,
        params_seq: Sequence[Sequence[Any]],
    ) -> None:
        """Execute a SQL statement for each parameter set."""
        await self.connection.executemany(sql, params_seq)
        await self.connection.commit()

    async def execute_script(self, sql: str) -> None:
        """Execute a multi-statement SQL script."""
        await self.connection.executescript(sql)

    async def fetch_one(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> dict[str, Any] | None:
        """Return a single row as a dict, or None."""
        cursor = await self.connection.execute(sql, params or [])
        return await cursor.fetchone()  # type: ignore[return-value]

    async def fetch_all(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all matching rows as dicts."""
        cursor = await self.connection.execute(sql, params or [])
        return await cursor.fetchall()  # type: ignore[return-value]

    async def fetch_val(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> Any:
        """Return the first column of the first row (scalar)."""
        # Temporarily bypass row_factory for scalar access
        conn = self.connection
        old_factory = conn.row_factory
        conn.row_factory = None  # type: ignore[assignment]
        try:
            cursor = await conn.execute(sql, params or [])
            row = await cursor.fetchone()
            return row[0] if row else None  # type: ignore[index]
        finally:
            conn.row_factory = old_factory  # type: ignore[assignment]

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Explicit transaction scope.

        Usage::

            async with db.transaction():
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")
        """
        conn = self.connection
        # aiosqlite auto-begins; we just need to commit/rollback
        try:
            yield
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    @property
    def repos(self) -> _RepositoryBundle:
        """Lazy-init bundle of all repositories."""
        if self._repos is None:
            self._repos = _RepositoryBundle(self)
        return self._repos


class _RepositoryBundle:
    """Aggregates all repositories for convenient access via ``db.repos.*``."""

    def __init__(self, db: Database) -> None:
        # Lazy imports to avoid circular references
        from wine_crawler.admin.db.repositories.crawl_rules import CrawlRulesRepository
        from wine_crawler.admin.db.repositories.credentials import CredentialsRepository
        from wine_crawler.admin.db.repositories.job_logs import JobLogsRepository
        from wine_crawler.admin.db.repositories.jobs import JobsRepository
        from wine_crawler.admin.db.repositories.kv_store import KVStoreRepository
        from wine_crawler.admin.db.repositories.projects import ProjectsRepository
        from wine_crawler.admin.db.repositories.request_kits import RequestKitsRepository
        from wine_crawler.admin.db.repositories.rule_test_results import (
            RuleTestResultsRepository,
        )
        from wine_crawler.admin.db.repositories.rule_versions import RuleVersionsRepository
        from wine_crawler.admin.db.repositories.schedules import SchedulesRepository
        from wine_crawler.admin.db.repositories.site_capabilities import (
            SiteCapabilitiesRepository,
        )

        self.jobs = JobsRepository(db)
        self.job_logs = JobLogsRepository(db)
        self.credentials = CredentialsRepository(db)
        self.schedules = SchedulesRepository(db)
        self.request_kits = RequestKitsRepository(db)
        self.site_capabilities = SiteCapabilitiesRepository(db)
        self.projects = ProjectsRepository(db)
        self.crawl_rules = CrawlRulesRepository(db)
        self.rule_versions = RuleVersionsRepository(db)
        self.rule_test_results = RuleTestResultsRepository(db)
        self.kv_store = KVStoreRepository(db)
