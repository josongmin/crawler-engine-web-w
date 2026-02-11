# pyright: reportUnnecessaryTypeIgnoreComment=false
# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownVariableType=false
# browserforge library doesn't have complete type stubs, type ignores are necessary

"""Coherent browser persona generation and caching via browserforge.

A "persona" is a consistent set of browser fingerprint attributes (user-agent,
viewport, screen, WebGL renderer, platform, languages, HTTP headers) that looks
like a single real user.  Re-using the same persona across sessions avoids the
"new identity every visit" signal that trips bot detectors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from browserforge.fingerprints import FingerprintGenerator
from browserforge.headers import HeaderGenerator

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Persona:
    """Immutable snapshot of a generated browser identity."""

    user_agent: str
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    locale: str
    timezone_id: str
    platform: str
    http_headers: dict[str, str] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    raw_fingerprint: dict[str, Any] = field(default_factory=dict, repr=False)  # pyright: ignore[reportUnknownVariableType]


def generate_persona(
    *,
    browser: str = "chrome",
    os: str = "macos",
) -> Persona:
    """Generate a coherent browser persona.

    All attributes (UA, viewport, screen, platform, etc.) are internally
    consistent -- e.g. a Chrome-on-macOS UA will have matching screen sizes and
    platform strings.  This avoids fingerprint mismatches that flag bots.
    """
    # browserforge types are not fully typed
    fg = FingerprintGenerator(browser=browser, os=os)  # type: ignore[reportUnknownVariableType]
    fp = fg.generate()  # type: ignore[reportUnknownVariableType]

    hg = HeaderGenerator(browser=browser, os=os)  # type: ignore[reportUnknownVariableType]
    headers = hg.generate()  # type: ignore[reportUnknownVariableType]

    # Extract navigator props from fingerprint
    nav = fp.navigator if hasattr(fp, "navigator") else fp.get("navigator", {})  # type: ignore[union-attr]
    screen = fp.screen if hasattr(fp, "screen") else fp.get("screen", {})  # type: ignore[union-attr]

    # Handle both attribute and dict access
    def _get(obj: Any, key: str, default: Any = "") -> Any:
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            return obj.get(key, default)  # type: ignore[reportUnknownVariableType]
        return default

    ua = _get(nav, "userAgent", "")
    platform = _get(nav, "platform", "MacIntel")
    locale = _get(nav, "language", "en-US")

    vw = _get(screen, "width", 1920)
    vh = _get(screen, "height", 1080)
    sw = _get(screen, "availWidth", vw)
    sh = _get(screen, "availHeight", vh)

    # Build clean HTTP header dict (lowercase keys for Playwright)
    http_headers: dict[str, str] = {}
    if hasattr(headers, "items"):
        # browserforge headers type is not fully typed
        http_headers = {k: v for k, v in headers.items() if k.lower() != "user-agent"}  # type: ignore[reportUnknownVariableType]

    # Serialize the raw fingerprint for caching
    raw: dict[str, Any] = {}
    try:
        if hasattr(fp, "model_dump"):
            raw_result: Any = fp.model_dump()  # type: ignore[union-attr, reportUnknownVariableType]
            if isinstance(raw_result, dict):
                # Cast to dict[str, Any] for type checker
                raw = dict[str, Any](raw_result)  # type: ignore[arg-type]
        elif hasattr(fp, "dict"):
            raw_result: Any = fp.dict()  # type: ignore[union-attr, reportUnknownVariableType]
            if isinstance(raw_result, dict):
                # Cast to dict[str, Any] for type checker
                raw = dict[str, Any](raw_result)  # type: ignore[arg-type]
        elif isinstance(fp, dict):
            # Cast to dict[str, Any] for type checker
            raw = dict[str, Any](fp)  # type: ignore[arg-type]
    except Exception:
        pass

    return Persona(
        user_agent=ua,
        viewport_width=int(vw),
        viewport_height=int(vh),
        screen_width=int(sw),
        screen_height=int(sh),
        locale=locale,
        timezone_id="America/New_York",  # sensible default
        platform=platform,
        http_headers=http_headers,
        raw_fingerprint=raw,
    )


# ---------------------------------------------------------------------------
# Persona persistence
# ---------------------------------------------------------------------------


def _persona_to_dict(p: Persona) -> dict[str, Any]:
    return {
        "user_agent": p.user_agent,
        "viewport_width": p.viewport_width,
        "viewport_height": p.viewport_height,
        "screen_width": p.screen_width,
        "screen_height": p.screen_height,
        "locale": p.locale,
        "timezone_id": p.timezone_id,
        "platform": p.platform,
        "http_headers": p.http_headers,
    }


def _persona_from_dict(d: dict[str, Any]) -> Persona:
    return Persona(
        user_agent=d["user_agent"],
        viewport_width=d["viewport_width"],
        viewport_height=d["viewport_height"],
        screen_width=d["screen_width"],
        screen_height=d["screen_height"],
        locale=d["locale"],
        timezone_id=d["timezone_id"],
        platform=d["platform"],
        http_headers=d.get("http_headers", {}),
    )


def save_persona(persona: Persona, path: Path) -> None:
    """Write persona to disk as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(_persona_to_dict(persona), indent=2), encoding="utf-8")


def load_persona(path: Path) -> Persona | None:
    """Load persona from disk.  Returns None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _persona_from_dict(data)
    except Exception:
        return None


def get_or_create_persona(
    cache_path: Path,
    *,
    browser: str = "chrome",
    os: str = "macos",
    force_new: bool = False,
) -> Persona:
    """Return a cached persona, or generate & cache a new one."""
    if not force_new:
        cached = load_persona(cache_path)
        if cached is not None:
            return cached

    persona = generate_persona(browser=browser, os=os)
    save_persona(persona, cache_path)
    return persona
