"""Database layer - async SQLite via aiosqlite.

Public API
----------
::

    from wine_crawler.admin.db import Database

    db = Database(Path("admin.db"))
    await db.connect()
    ...
    await db.disconnect()

Repositories are accessible via ``db.repos``:

::

    job = await db.repos.jobs.get(job_id)
"""

from __future__ import annotations

from wine_crawler.admin.db.connection import Database

__all__ = ["Database"]
