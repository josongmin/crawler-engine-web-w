"""Repository for the ``workflow_node_logs`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import WorkflowNodeLog, WorkflowNodeLogCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class WorkflowNodeLogsRepository(BaseRepository[WorkflowNodeLog]):
    _table = "workflow_node_logs"
    _pk = "id"
    _model = WorkflowNodeLog

    async def create(self, data: WorkflowNodeLogCreate) -> WorkflowNodeLog:
        """Append a log entry for a workflow node."""
        now = utcnow()
        _ = await self._db.execute(
            ("INSERT INTO workflow_node_logs (run_id, node_id, level, message, timestamp, data_json) "
             "VALUES (?, ?, ?, ?, ?, ?)"),
            [data.run_id, data.node_id, data.level, data.message, now, data.data_json],
        )
        lid = await self._db.fetch_val("SELECT last_insert_rowid()")
        return await self.get(lid)  # type: ignore[return-value]

    async def list_by_run(
        self,
        run_id: str,
        *,
        node_id: str | None = None,
        limit: int = 500,
    ) -> list[WorkflowNodeLog]:
        """Get logs for a run, optionally filtered by node."""
        if node_id:
            return await self.find_by(
                run_id=run_id, node_id=node_id, order_by="timestamp ASC", limit=limit
            )
        return await self.find_by(run_id=run_id, order_by="timestamp ASC", limit=limit)
