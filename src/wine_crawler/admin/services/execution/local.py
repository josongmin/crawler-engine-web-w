"""Local executor (in-process job execution)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wine_crawler.admin.db.models import Job


class LocalExecutor:
    """Execute jobs in the same process (current implementation)."""

    async def submit(self, job: Job) -> str:
        """Execute job locally (synchronous for now)."""
        # TODO: Implement actual crawler execution
        # This should call the existing crawler logic from wine_crawler.core
        return job.id
