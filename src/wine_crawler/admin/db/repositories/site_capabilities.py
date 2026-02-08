"""Repository for the ``site_capabilities`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import SiteCapability, SiteCapabilityUpsert, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class SiteCapabilitiesRepository(BaseRepository[SiteCapability]):
    _table = "site_capabilities"
    _pk = "site"
    _model = SiteCapability

    async def upsert_capability(self, data: SiteCapabilityUpsert) -> SiteCapability:
        """Insert or replace capabilities for a site."""
        now = utcnow()
        row = {
            "site": data.site,
            "supports_request_kit": int(data.supports_request_kit),
            "logout_strategy": data.logout_strategy,
            "login_validator": data.login_validator,
            "token_validator": data.token_validator,
            "csrf_required": int(data.csrf_required),
            "csrf_source": data.csrf_source,
            "csrf_key": data.csrf_key,
            "updated_at": now,
        }
        await self.upsert(row)
        return await self.get(data.site)  # type: ignore[return-value]

    async def list_sites(self) -> list[str]:
        """Return all site names with registered capabilities."""
        rows = await self._db.fetch_all("SELECT site FROM site_capabilities ORDER BY site")
        return [r["site"] for r in rows]
