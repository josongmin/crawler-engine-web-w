"""Repository for the ``job_logs`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import JobLog, JobLogCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class JobLogsRepository(BaseRepository[JobLog]):
    _table = "job_logs"
    _pk = "id"
    _model = JobLog

    async def create(self, data: JobLogCreate) -> JobLog:
        """Append a log entry to a job."""
        now = utcnow()
        row = {
            "job_id": data.job_id,
            "level": data.level,
            "message": data.message,
            "timestamp": now,
            "source": data.source,
        }
        cursor = await self._db.execute(
            """INSERT INTO job_logs (job_id, level, message, timestamp, source)
               VALUES (?, ?, ?, ?, ?)""",
            [row["job_id"], row["level"], row["message"], row["timestamp"], row["source"]],
        )
        log_id = cursor.lastrowid
        return await self.get(log_id)  # type: ignore[return-value]

    async def list_by_job(
        self,
        job_id: str,
        *,
        level: str | None = None,
        limit: int = 500,
        after_id: int | None = None,
    ) -> list[JobLog]:
        """Get logs for a job, optionally filtered by level, supporting cursor pagination."""
        params: list = [job_id]
        sql = "SELECT * FROM job_logs WHERE job_id = ?"

        if level:
            sql += " AND level = ?"
            params.append(level)
        if after_id is not None:
            sql += " AND id > ?"
            params.append(after_id)

        sql += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        rows = await self._db.fetch_all(sql, params)
        return [JobLog(**r) for r in rows]

    async def delete_by_job(self, job_id: str) -> int:
        """Delete all logs for a job. Returns the count deleted."""
        cursor = await self._db.execute(
            "DELETE FROM job_logs WHERE job_id = ?",
            [job_id],
        )
        return cursor.rowcount or 0
