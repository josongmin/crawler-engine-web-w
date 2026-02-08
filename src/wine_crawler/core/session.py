"""Persistent session manager.

Each site gets a directory under ``storage_state/<site>/`` containing:

  state.json         Playwright storage-state (cookies, localStorage, …)
  persona.json       browserforge fingerprint cache
  session.meta.json  Metadata (created_at, last_used_at, TTL, use_count, …)

The ``SessionManager`` transparently loads / validates / refreshes these
artifacts so individual crawlers never need to think about file paths.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from wine_crawler.core.fingerprint import Persona, get_or_create_persona, load_persona

if TYPE_CHECKING:
    from pathlib import Path

    from wine_crawler.config import Settings

# ---------------------------------------------------------------------------
# Session metadata
# ---------------------------------------------------------------------------


@dataclass
class SessionMeta:
    """Mutable bookkeeping that lives alongside Playwright's storage state."""

    site: str
    created_at: str = ""
    last_used_at: str = ""
    last_login_at: str = ""
    last_logout_at: str = ""
    use_count: int = 0
    ttl_hours: int = 72  # default: 3 days
    user_agent: str = ""
    status: str = "inactive"  # inactive | active | expired | logged_out

    # Convenience ------------------------------------------------------------

    @property
    def created_dt(self) -> datetime | None:
        return _parse_iso(self.created_at)

    @property
    def last_used_dt(self) -> datetime | None:
        return _parse_iso(self.last_used_at)

    @property
    def last_login_dt(self) -> datetime | None:
        return _parse_iso(self.last_login_at)

    @property
    def last_logout_dt(self) -> datetime | None:
        return _parse_iso(self.last_logout_at)

    @property
    def is_cleanly_closed(self) -> bool:
        """True if the last action was a logout (no dangling server session)."""
        if not self.last_logout_at:
            return False
        login_dt = self.last_login_dt
        logout_dt = self.last_logout_dt
        if login_dt is None or logout_dt is None:
            return False
        return logout_dt >= login_dt

    @property
    def expires_at(self) -> datetime | None:
        base = self.last_login_dt or self.created_dt
        if base is None:
            return None
        return base + timedelta(hours=self.ttl_hours)

    @property
    def is_expired(self) -> bool:
        exp = self.expires_at
        if exp is None:
            return True
        return _now() > exp

    @property
    def age_human(self) -> str:
        """Human-readable age since creation."""
        dt = self.created_dt
        if dt is None:
            return "n/a"
        return _humanize_delta(_now() - dt)

    @property
    def freshness_human(self) -> str:
        """Human-readable time since last use."""
        dt = self.last_used_dt
        if dt is None:
            return "never"
        return _humanize_delta(_now() - dt) + " ago"

    @property
    def ttl_remaining_human(self) -> str:
        exp = self.expires_at
        if exp is None:
            return "n/a"
        remaining = exp - _now()
        if remaining.total_seconds() <= 0:
            return "expired"
        return _humanize_delta(remaining)


# ---------------------------------------------------------------------------
# Session directory layout
# ---------------------------------------------------------------------------


def _session_dir(settings: Settings, site: str) -> Path:
    return settings.storage_state_dir / site


def _state_path(settings: Settings, site: str) -> Path:
    return _session_dir(settings, site) / "state.json"


def _persona_path(settings: Settings, site: str) -> Path:
    return _session_dir(settings, site) / "persona.json"


def _meta_path(settings: Settings, site: str) -> Path:
    return _session_dir(settings, site) / "session.meta.json"


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class SessionManager:
    """High-level façade for per-site session persistence."""

    def __init__(self, settings: Settings, site: str, *, ttl_hours: int = 72) -> None:
        self._settings = settings
        self._site = site
        self._ttl_hours = ttl_hours
        self._dir = _session_dir(settings, site)
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- paths --

    @property
    def state_path(self) -> Path:
        """Playwright storage-state JSON."""
        return _state_path(self._settings, self._site)

    @property
    def persona_path(self) -> Path:
        """browserforge persona JSON."""
        return _persona_path(self._settings, self._site)

    @property
    def meta_path(self) -> Path:
        return _meta_path(self._settings, self._site)

    @property
    def session_dir(self) -> Path:
        return self._dir

    # -- metadata --

    def load_meta(self) -> SessionMeta:
        if self.meta_path.exists():
            try:
                raw = json.loads(self.meta_path.read_text(encoding="utf-8"))
                return SessionMeta(
                    **{k: v for k, v in raw.items() if k in SessionMeta.__dataclass_fields__}
                )
            except Exception:
                pass
        return SessionMeta(site=self._site, ttl_hours=self._ttl_hours)

    def save_meta(self, meta: SessionMeta) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(
            json.dumps(asdict(meta), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # -- persona --

    def get_or_create_persona(self, *, force_new: bool = False) -> Persona:
        return get_or_create_persona(self.persona_path, force_new=force_new)

    def load_persona(self) -> Persona | None:
        return load_persona(self.persona_path)

    # -- lifecycle --

    @property
    def has_session(self) -> bool:
        """True if all three artifacts exist on disk."""
        return self.state_path.exists() and self.meta_path.exists()

    @property
    def is_expired(self) -> bool:
        if not self.has_session:
            return True
        return self.load_meta().is_expired

    @property
    def is_usable(self) -> bool:
        """Session exists AND hasn't expired."""
        return self.has_session and not self.is_expired

    def touch(self) -> SessionMeta:
        """Bump ``last_used_at`` and ``use_count``.  Call on every browser use."""
        meta = self.load_meta()
        meta.last_used_at = _now_iso()
        meta.use_count += 1
        self.save_meta(meta)
        return meta

    def mark_login(self, *, user_agent: str = "") -> SessionMeta:
        """Record a successful login."""
        meta = self.load_meta()
        now = _now_iso()
        if not meta.created_at:
            meta.created_at = now
        meta.last_login_at = now
        meta.last_used_at = now
        meta.use_count += 1
        meta.status = "active"
        meta.ttl_hours = self._ttl_hours
        if user_agent:
            meta.user_agent = user_agent
        self.save_meta(meta)
        return meta

    def mark_logout(self) -> SessionMeta:
        """Record a successful logout."""
        meta = self.load_meta()
        meta.last_logout_at = _now_iso()
        meta.last_used_at = _now_iso()
        meta.status = "logged_out"
        self.save_meta(meta)
        return meta

    def mark_expired(self) -> None:
        meta = self.load_meta()
        meta.status = "expired"
        self.save_meta(meta)

    def clear(self) -> None:
        """Delete ALL session artifacts for this site."""
        if self._dir.exists():
            shutil.rmtree(self._dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- migration from legacy flat files --

    def migrate_legacy(self) -> bool:
        """Move old ``storage_state/<site>.json`` / ``<site>_persona.json``
        into the new directory layout.  Returns True if anything moved."""
        moved = False
        parent = self._settings.storage_state_dir

        legacy_state = parent / f"{self._site}.json"
        if legacy_state.exists() and not self.state_path.exists():
            shutil.move(str(legacy_state), str(self.state_path))
            moved = True

        legacy_persona = parent / f"{self._site}_persona.json"
        if legacy_persona.exists() and not self.persona_path.exists():
            shutil.move(str(legacy_persona), str(self.persona_path))
            moved = True

        # Create initial meta if we migrated files but have none
        if moved and not self.meta_path.exists():
            now = _now_iso()
            meta = SessionMeta(
                site=self._site,
                created_at=now,
                last_used_at=now,
                last_login_at=now,
                use_count=1,
                ttl_hours=self._ttl_hours,
                status="active",
            )
            persona = self.load_persona()
            if persona:
                meta.user_agent = persona.user_agent
            self.save_meta(meta)
        return moved


# ---------------------------------------------------------------------------
# Listing helpers (for CLI)
# ---------------------------------------------------------------------------


def list_sessions(settings: Settings) -> list[SessionMeta]:
    """Return metadata for every site that has a session directory."""
    results: list[SessionMeta] = []
    base = settings.storage_state_dir
    if not base.exists():
        return results
    for child in sorted(base.iterdir()):
        if child.is_dir():
            meta_file = child / "session.meta.json"
            if meta_file.exists():
                try:
                    raw = json.loads(meta_file.read_text(encoding="utf-8"))
                    meta = SessionMeta(
                        **{k: v for k, v in raw.items() if k in SessionMeta.__dataclass_fields__}
                    )
                    # Refresh status
                    if meta.status == "active" and meta.is_expired:
                        meta.status = "expired"
                    results.append(meta)
                except Exception:
                    continue
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _humanize_delta(delta: timedelta) -> str:
    total_secs = int(delta.total_seconds())
    if total_secs < 0:
        return "0s"
    days, remainder = divmod(total_secs, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)
