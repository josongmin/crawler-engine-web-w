"""Repository for the ``rule_versions`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import RuleVersion, RuleVersionCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class RuleVersionsRepository(BaseRepository[RuleVersion]):
    _table = "rule_versions"
    _pk = "id"
    _model = RuleVersion

    async def create(self, data: RuleVersionCreate) -> RuleVersion:
        """Snapshot a rule version."""
        now = utcnow()
        cursor = await self._db.execute(
            """INSERT INTO rule_versions (rule_id, version, rule_body, change_note, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            [data.rule_id, data.version, data.rule_body, data.change_note, now],
        )
        vid = cursor.lastrowid
        return await self.get(vid)  # type: ignore[return-value]

    async def list_by_rule(self, rule_id: str) -> list[RuleVersion]:
        """All versions for a rule, ordered by version descending."""
        return await self.find_by(rule_id=rule_id, order_by="version DESC")

    async def get_version(self, rule_id: str, version: int) -> RuleVersion | None:
        """Get a specific version of a rule."""
        row = await self._db.fetch_one(
            "SELECT * FROM rule_versions WHERE rule_id = ? AND version = ?",
            [rule_id, version],
        )
        return RuleVersion(**row) if row else None

    async def latest_version(self, rule_id: str) -> RuleVersion | None:
        """Get the most recent version snapshot."""
        row = await self._db.fetch_one(
            "SELECT * FROM rule_versions WHERE rule_id = ? ORDER BY version DESC LIMIT 1",
            [rule_id],
        )
        return RuleVersion(**row) if row else None
