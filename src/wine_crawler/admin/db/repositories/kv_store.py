"""Repository for the ``kv_store`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import KVEntry
from wine_crawler.admin.db.repositories.base import BaseRepository


class KVStoreRepository(BaseRepository[KVEntry]):
    _table = "kv_store"
    _pk = "key"
    _model = KVEntry

    async def get_value(self, key: str) -> str | None:
        """Get a value by key, or None if not found."""
        row = await self._db.fetch_one(
            "SELECT value FROM kv_store WHERE key = ?",
            [key],
        )
        return row["value"] if row else None

    async def set_value(self, key: str, value: str) -> None:
        """Set a key-value pair (upsert)."""
        await self.upsert({"key": key, "value": value})

    async def delete_key(self, key: str) -> bool:
        """Remove a key. Returns True if it existed."""
        return await self.delete(key)

    async def get_many(self, prefix: str) -> dict[str, str]:
        """Get all entries whose key starts with a prefix."""
        rows = await self._db.fetch_all(
            "SELECT key, value FROM kv_store WHERE key LIKE ?",
            [f"{prefix}%"],
        )
        return {r["key"]: r["value"] for r in rows}
