"""Repository for the ``credentials`` table."""

from __future__ import annotations

from wine_crawler.admin.db.models import Credential, CredentialUpsert, utcnow
from wine_crawler.admin.db.repositories.base import BaseRepository


class CredentialsRepository(BaseRepository[Credential]):
    _table = "credentials"
    _pk = "site"
    _model = Credential

    async def upsert_credential(self, data: CredentialUpsert) -> Credential:
        """Insert or update credentials for a site."""
        now = utcnow()
        row = {
            "site": data.site,
            "email": data.email,
            "password_enc": data.password_enc,
            "notes": data.notes,
            "updated_at": now,
        }
        await self.upsert(row)
        return await self.get(data.site)  # type: ignore[return-value]

    async def list_sites(self) -> list[str]:
        """Return all site names that have stored credentials."""
        rows = await self._db.fetch_all("SELECT site FROM credentials ORDER BY site")
        return [r["site"] for r in rows]
