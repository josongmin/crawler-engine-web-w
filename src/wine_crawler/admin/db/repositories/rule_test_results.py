"""Repository for the ``rule_test_results`` table."""

from __future__ import annotations

from uuid import uuid4

from wine_crawler.admin.db.models import RuleTestResult, RuleTestResultCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class RuleTestResultsRepository(BaseRepository[RuleTestResult]):
    _table = "rule_test_results"
    _pk = "id"
    _model = RuleTestResult

    async def create(self, data: RuleTestResultCreate) -> RuleTestResult:
        """Store a rule test result."""
        now = utcnow()
        rid = str(uuid4())
        row = {
            "id": rid,
            "rule_id": data.rule_id,
            "test_url": data.test_url,
            "status": data.status,
            "extracted": data.extracted,
            "errors": data.errors,
            "screenshot": data.screenshot,
            "duration_ms": data.duration_ms,
            "created_at": now,
        }
        await self.insert(row)
        return await self.get(rid)  # type: ignore[return-value]

    async def list_by_rule(
        self,
        rule_id: str,
        *,
        limit: int = 20,
    ) -> list[RuleTestResult]:
        """Recent test results for a rule."""
        return await self.find_by(rule_id=rule_id, order_by="created_at DESC", limit=limit)
