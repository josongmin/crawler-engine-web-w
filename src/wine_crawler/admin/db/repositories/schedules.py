"""Repository for the ``schedules`` table."""

from __future__ import annotations

from uuid import uuid4

from wine_crawler.admin.db.models import Schedule, ScheduleCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class SchedulesRepository(BaseRepository[Schedule]):
    _table = "schedules"
    _pk = "id"
    _model = Schedule

    async def create(self, data: ScheduleCreate) -> Schedule:
        """Create a new schedule."""
        now = utcnow()
        sid = str(uuid4())
        row = {
            "id": sid,
            "site": data.site,
            "project_id": data.project_id,
            "rule_id": data.rule_id,
            "cron_expr": data.cron_expr,
            "limit_n": data.limit_n,
            "enabled": int(data.enabled),
            "created_at": now,
        }
        await self.insert(row)
        return await self.get(sid)  # type: ignore[return-value]

    async def list_enabled(self) -> list[Schedule]:
        """Return all enabled schedules."""
        return await self.find_by(enabled=1, order_by="site, created_at")

    async def mark_run(self, schedule_id: str, next_run: str | None = None) -> bool:
        """Update last_run timestamp and optionally set next_run."""
        now = utcnow()
        data = {"last_run": now}
        if next_run is not None:
            data["next_run"] = next_run
        return await self.update(schedule_id, data)
