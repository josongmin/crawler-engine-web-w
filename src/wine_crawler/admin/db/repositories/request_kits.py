"""Repository for the ``request_kits`` table."""

from __future__ import annotations

from uuid import uuid4

from wine_crawler.admin.db.models import RequestKit, RequestKitCreate, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class RequestKitsRepository(BaseRepository[RequestKit]):
    _table = "request_kits"
    _pk = "id"
    _model = RequestKit

    async def create(self, data: RequestKitCreate) -> RequestKit:
        """Store a newly exported request kit."""
        now = utcnow()
        kit_id = str(uuid4())
        row = {
            "id": kit_id,
            "site": data.site,
            "format": data.format,
            "snippet_enc": data.snippet_enc,
            "cookies_enc": data.cookies_enc,
            "headers_enc": data.headers_enc,
            "csrf_extractor": data.csrf_extractor,
            "user_agent": data.user_agent,
            "expires_at": data.expires_at,
            "created_at": now,
            "used_count": 0,
            "notes": data.notes,
        }
        await self.insert(row)
        return await self.get(kit_id)  # type: ignore[return-value]

    async def latest_for_site(self, site: str) -> RequestKit | None:
        """Get the most recently created kit for a site."""
        row = await self._db.fetch_one(
            "SELECT * FROM request_kits WHERE site = ? ORDER BY created_at DESC LIMIT 1",
            [site],
        )
        return RequestKit(**row) if row else None

    async def list_by_site(
        self,
        site: str,
        *,
        limit: int = 20,
    ) -> list[RequestKit]:
        """History of exported kits for a site."""
        return await self.find_by(site=site, order_by="created_at DESC", limit=limit)

    async def increment_used(self, kit_id: str) -> bool:
        """Bump usage counter and timestamp."""
        now = utcnow()
        cursor = await self._db.execute(
            "UPDATE request_kits SET used_count = used_count + 1, last_used = ? WHERE id = ?",
            [now, kit_id],
        )
        return (cursor.rowcount or 0) > 0
