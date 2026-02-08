"""Repository for the ``projects`` table."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from wine_crawler.admin.db.models import Project, ProjectCreate, ProjectUpdate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class ProjectsRepository(BaseRepository[Project]):
    _table = "projects"
    _pk = "id"
    _model = Project

    async def create(self, data: ProjectCreate) -> Project:
        """Create a new project."""
        now = utcnow()
        pid = str(uuid4())
        row = {
            "id": pid,
            "name": data.name,
            "site": data.site,
            "description": data.description,
            "status": data.status,
            "created_at": now,
            "updated_at": now,
        }
        await self.insert(row)
        return await self.get(pid)  # type: ignore[return-value]

    async def update_project(self, project_id: str, data: ProjectUpdate) -> bool:
        """Partial update with auto-refreshed ``updated_at``."""
        changes = data.model_dump(exclude_none=True)
        if not changes:
            return False
        changes["updated_at"] = utcnow()
        return await self.update(project_id, changes)

    async def get_by_name(self, name: str) -> Project | None:
        """Lookup project by unique name."""
        row = await self._db.fetch_one(
            "SELECT * FROM projects WHERE name = ?",
            [name],
        )
        return Project(**row) if row else None

    async def list_by_site(self, site: str) -> list[Project]:
        """Return all projects for a given site."""
        return await self.find_by(site=site, order_by="created_at DESC")

    async def get_stats(self, project_id: str) -> dict[str, Any]:
        """Aggregate stats for a project (rules count, jobs count, last run)."""
        rules = await self._db.fetch_val(
            "SELECT COUNT(*) FROM crawl_rules WHERE project_id = ?",
            [project_id],
        )
        jobs = await self._db.fetch_val(
            "SELECT COUNT(*) FROM jobs WHERE project_id = ?",
            [project_id],
        )
        last_job = await self._db.fetch_one(
            "SELECT finished_at, status FROM jobs WHERE project_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            [project_id],
        )
        return {
            "rules_count": rules or 0,
            "jobs_count": jobs or 0,
            "last_job_finished_at": last_job["finished_at"] if last_job else None,
            "last_job_status": last_job["status"] if last_job else None,
        }
