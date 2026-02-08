"""Repository for the ``jobs`` table."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from wine_crawler.admin.db.models import Job, JobCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class JobsRepository(BaseRepository[Job]):
    _table = "jobs"
    _pk = "id"
    _model = Job

    async def create(self, data: JobCreate) -> Job:
        """Create a new job and return it."""
        now = utcnow()
        job_id = str(uuid4())
        row = {
            "id": job_id,
            "site": data.site,
            "project_id": data.project_id,
            "rule_id": data.rule_id,
            "executor": data.executor,
            "executor_meta": data.executor_meta,
            "status": "pending",
            "limit_n": data.limit_n,
            "headless": int(data.headless),
            "created_at": now,
            "item_count": 0,
            "meta": data.meta,
        }
        await self.insert(row)
        return await self.get(job_id)  # type: ignore[return-value]

    async def update_status(
        self,
        job_id: str,
        status: str,
        *,
        error: str | None = None,
        item_count: int | None = None,
        output_path: str | None = None,
    ) -> bool:
        """Convenience: update job status and optional completion fields."""
        now = utcnow()
        data: dict[str, Any] = {"status": status}

        if status == "running":
            data["started_at"] = now
        elif status in ("completed", "failed", "cancelled"):
            data["finished_at"] = now
            if (started := (await self.get(job_id))) and started.started_at:
                from datetime import datetime

                start = datetime.fromisoformat(started.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(now.replace("Z", "+00:00"))
                data["duration_ms"] = int((end - start).total_seconds() * 1000)

        if error is not None:
            data["error"] = error
        if item_count is not None:
            data["item_count"] = item_count
        if output_path is not None:
            data["output_path"] = output_path

        return await self.update(job_id, data)

    async def list_by_site(
        self,
        site: str,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Job]:
        """List jobs for a site, optionally filtered by status."""
        filters: dict[str, Any] = {"site": site}
        if status:
            filters["status"] = status
        return await self.find_by(
            order_by="created_at DESC",
            limit=limit,
            **filters,
        )

    async def list_recent(self, *, limit: int = 20) -> list[Job]:
        """Most recent jobs across all sites."""
        return await self.list_all(order_by="created_at DESC", limit=limit)
