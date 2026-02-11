# pyright: reportUnnecessaryTypeIgnoreComment=false
# Cursor.rowcount exists but type stubs don't include it

"""Base repository with common CRUD helpers.

Subclasses define ``_table``, ``_pk``, ``_model`` and get typed CRUD for free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from wine_crawler.admin.db.connection import Database

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Generic async repository for a single SQLite table.

    Subclasses must set:
        _table  - table name
        _pk     - primary key column name (default ``"id"``)
        _model  - Pydantic model class for row -> model conversion
    """

    _table: str = ""
    _pk: str = "id"
    _model: type[T]  # pyright: ignore[reportUninitializedInstanceVariable]

    def __init__(self, db: Database) -> None:
        # BaseRepository doesn't inherit from any class, so no super() call needed
        self._db = db
        # Subclasses must set _table and _model
        if not self._table:
            raise RuntimeError(f"{self.__class__.__name__} must set _table class variable")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, pk: Any) -> T | None:
        """Fetch one row by primary key."""
        row = await self._db.fetch_one(
            f"SELECT * FROM {self._table} WHERE {self._pk} = ?",
            [pk],
        )
        return self._model(**row) if row else None

    async def list_all(
        self,
        *,
        order_by: str = "",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[T]:
        """Return all rows, optionally ordered/paginated."""
        sql = f"SELECT * FROM {self._table}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"
        rows = await self._db.fetch_all(sql)
        return [self._model(**r) for r in rows]

    async def find_by(
        self,
        *,
        order_by: str = "",
        limit: int | None = None,
        offset: int = 0,
        **filters: Any,
    ) -> list[T]:
        """Filter rows by column=value pairs.

        Usage::

            await repo.find_by(site="burghound", status="active")
        """
        if not filters:
            return await self.list_all(order_by=order_by, limit=limit, offset=offset)

        clauses: list[str] = []
        values: list[Any] = []
        for col, val in filters.items():
            if val is None:
                clauses.append(f"{col} IS NULL")
            else:
                clauses.append(f"{col} = ?")
                values.append(val)

        sql = f"SELECT * FROM {self._table} WHERE {' AND '.join(clauses)}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"

        rows = await self._db.fetch_all(sql, values)
        return [self._model(**r) for r in rows]

    async def count(self, **filters: Any) -> int:
        """Count rows, optionally filtered."""
        if not filters:
            val = await self._db.fetch_val(f"SELECT COUNT(*) FROM {self._table}")
            return val or 0

        clauses: list[str] = []
        values: list[Any] = []
        for col, val in filters.items():
            if val is None:
                clauses.append(f"{col} IS NULL")
            else:
                clauses.append(f"{col} = ?")
                values.append(val)

        sql = f"SELECT COUNT(*) FROM {self._table} WHERE {' AND '.join(clauses)}"
        result = await self._db.fetch_val(sql, values)
        return result or 0

    async def exists(self, pk: Any) -> bool:
        """Check if a row exists by primary key."""
        val = await self._db.fetch_val(
            f"SELECT 1 FROM {self._table} WHERE {self._pk} = ?",
            [pk],
        )
        return val is not None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def insert(self, data: dict[str, Any]) -> None:
        """Insert a single row from a dict."""
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)
        _ = await self._db.execute(
            f"INSERT INTO {self._table} ({col_names}) VALUES ({placeholders})",
            list(data.values()),
        )

    async def update(self, pk: Any, data: dict[str, Any]) -> bool:
        """Update a row by primary key. Returns True if a row was modified."""
        # Filter out None values so partial updates work
        filtered = {k: v for k, v in data.items() if v is not None}
        if not filtered:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = [*list(filtered.values()), pk]
        cursor = await self._db.execute(
            f"UPDATE {self._table} SET {set_clause} WHERE {self._pk} = ?",
            values,
        )
        # Cursor.rowcount exists but type checker doesn't recognize it
        return cursor.rowcount > 0  # type: ignore[attr-defined]

    async def delete(self, pk: Any) -> bool:
        """Delete a row by primary key. Returns True if a row was removed."""
        cursor = await self._db.execute(
            f"DELETE FROM {self._table} WHERE {self._pk} = ?",
            [pk],
        )
        # Cursor.rowcount exists but type checker doesn't recognize it
        return cursor.rowcount > 0  # type: ignore[attr-defined]

    async def upsert(self, data: dict[str, Any]) -> None:
        """Insert or replace a row (uses SQLite REPLACE)."""
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_names = ", ".join(cols)
        _ = await self._db.execute(
            f"INSERT OR REPLACE INTO {self._table} ({col_names}) VALUES ({placeholders})",
            list(data.values()),
        )
