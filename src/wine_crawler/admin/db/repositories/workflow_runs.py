"""Repository for the ``workflow_runs`` table."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from wine_crawler.admin.db.models import WorkflowRun, WorkflowRunCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class WorkflowRunsRepository(BaseRepository[WorkflowRun]):
    _table = "workflow_runs"
    _pk = "id"
    _model = WorkflowRun

    async def create(self, data: WorkflowRunCreate) -> WorkflowRun:
        """Create a new workflow run."""
        now = utcnow()
        run_id = str(uuid4())
        row = {
            "id": run_id,
            "workflow_id": data.workflow_id,
            "status": "pending",
            "created_at": now,
        }
        await self.insert(row)
        return await self.get(run_id)  # type: ignore[return-value]

    async def update_status(
        self,
        run_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> bool:
        """Update run status with automatic timestamp handling."""
        now = utcnow()
        data: dict[str, Any] = {"status": status}

        if status == "running":
            data["started_at"] = now
        elif status in ("completed", "failed", "cancelled"):
            data["finished_at"] = now
            run = await self.get(run_id)
            if run and run.started_at:
                start = datetime.fromisoformat(run.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(now.replace("Z", "+00:00"))
                data["duration_ms"] = int((end - start).total_seconds() * 1000)

        if error is not None:
            data["error"] = error

        return await self.update(run_id, data)

    async def update_node_states(self, run_id: str, states_json: str) -> bool:
        """Update the node_states_json field."""
        return await self.update(run_id, {"node_states_json": states_json})

    async def list_by_workflow(
        self, workflow_id: str, *, limit: int = 20
    ) -> list[WorkflowRun]:
        """List runs for a workflow, most recent first."""
        return await self.find_by(
            workflow_id=workflow_id, order_by="created_at DESC", limit=limit
        )
