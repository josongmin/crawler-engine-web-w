"""Repository for the ``workflows`` table."""

from __future__ import annotations

from uuid import uuid4

from wine_crawler.admin.db.models import Workflow, WorkflowCreate, WorkflowUpdate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class WorkflowsRepository(BaseRepository[Workflow]):
    _table = "workflows"
    _pk = "id"
    _model = Workflow

    async def create(self, data: WorkflowCreate) -> Workflow:
        """Create a new workflow and return it."""
        now = utcnow()
        wf_id = str(uuid4())
        row = {
            "id": wf_id,
            "name": data.name,
            "site": data.site,
            "description": data.description,
            "status": "draft",
            "graph_json": data.graph_json,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        await self.insert(row)
        return await self.get(wf_id)  # type: ignore[return-value]

    async def update_workflow(self, wf_id: str, data: WorkflowUpdate) -> bool:
        """Partial update with auto-refreshed updated_at."""
        changes = data.model_dump(exclude_none=True)
        if not changes:
            return False
        changes["updated_at"] = utcnow()
        return await self.update(wf_id, changes)

    async def list_by_site(self, site: str) -> list[Workflow]:
        """List workflows for a site."""
        return await self.find_by(site=site, order_by="updated_at DESC")

    async def list_recent(self, *, limit: int = 20) -> list[Workflow]:
        """Most recent workflows across all sites."""
        return await self.list_all(order_by="updated_at DESC", limit=limit)
