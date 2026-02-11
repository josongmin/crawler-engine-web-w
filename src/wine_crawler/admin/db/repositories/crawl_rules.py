"""Repository for the ``crawl_rules`` table."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from wine_crawler.admin.db.models import CrawlRule, CrawlRuleCreate, CrawlRuleUpdate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class CrawlRulesRepository(BaseRepository[CrawlRule]):
    _table = "crawl_rules"
    _pk = "id"
    _model = CrawlRule

    async def create(self, data: CrawlRuleCreate) -> CrawlRule:
        """Create a new crawl rule at version 1."""
        now = utcnow()
        rule_id = str(uuid4())
        row = {
            "id": rule_id,
            "project_id": data.project_id,
            "name": data.name,
            "page_type": data.page_type,
            "url_pattern": data.url_pattern,
            "version": 1,
            "rule_body": data.rule_body,
            "is_active": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": data.created_by,
        }
        await self.insert(row)
        return await self.get(rule_id)  # type: ignore[return-value]

    async def update_rule(self, rule_id: str, data: CrawlRuleUpdate) -> bool:
        """Partial update with auto-refreshed ``updated_at``."""
        changes = data.model_dump(exclude_none=True)
        if not changes:
            return False

        # Convert bool to int for SQLite
        if "is_active" in changes:
            changes["is_active"] = int(changes["is_active"])

        changes["updated_at"] = utcnow()
        return await self.update(rule_id, changes)

    async def bump_version(self, rule_id: str, new_body: str) -> CrawlRule | None:
        """Increment version and update rule_body atomically.

        Also creates a ``rule_versions`` snapshot (caller should use a transaction).
        """
        rule = await self.get(rule_id)
        if rule is None:
            return None

        new_version = rule.version + 1
        now = utcnow()
        _ = await self.update(
            rule_id,
            {
                "version": new_version,
                "rule_body": new_body,
                "updated_at": now,
            },
        )
        return await self.get(rule_id)

    async def list_by_project(
        self,
        project_id: str,
        *,
        active_only: bool = False,
    ) -> list[CrawlRule]:
        """Rules belonging to a project."""
        filters: dict[str, Any] = {"project_id": project_id}
        if active_only:
            filters["is_active"] = 1
        return await self.find_by(order_by="name ASC", **filters)

    async def get_active_by_name(
        self,
        project_id: str,
        name: str,
    ) -> CrawlRule | None:
        """Lookup an active rule by project + name."""
        row = await self._db.fetch_one(
            "SELECT * FROM crawl_rules WHERE project_id = ? AND name = ? AND is_active = 1",
            [project_id, name],
        )
        return CrawlRule(**row) if row else None
