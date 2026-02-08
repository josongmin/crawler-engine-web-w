"""Browser lifecycle management with stealth and fingerprint injection."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
from playwright_stealth import Stealth

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path
    from types import TracebackType

    from wine_crawler.config import Settings
    from wine_crawler.core.fingerprint import Persona


@dataclass(frozen=True)
class BrowserSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext


class BrowserManager:
    """Async context-manager that spins up a stealth Playwright browser.

    Layers applied:
      L1  playwright-stealth  (navigator.webdriver, chrome.runtime, …)
      L2  browserforge persona (coherent UA / viewport / headers)
      L5  proxy (optional)
    """

    def __init__(
        self,
        settings: Settings,
        *,
        storage_state: Path | None = None,
        persona: Persona | None = None,
    ) -> None:
        self._settings = settings
        self._storage_state = storage_state
        self._persona = persona
        self._stealth_cm: Any | None = None
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> BrowserSession:
        # L1: Wrap async_playwright with stealth patches
        self._stealth_cm = Stealth().use_async(async_playwright())
        self._pw = await self._stealth_cm.__aenter__()

        # L5: Proxy support
        launch_kwargs: dict[str, Any] = {
            "headless": self._settings.headless,
        }
        if self._settings.slow_mo_ms:
            launch_kwargs["slow_mo"] = self._settings.slow_mo_ms

        if self._settings.proxy_server:
            proxy: dict[str, str] = {"server": self._settings.proxy_server}
            if self._settings.proxy_username:
                proxy["username"] = self._settings.proxy_username
            if self._settings.proxy_password:
                proxy["password"] = self._settings.proxy_password
            launch_kwargs["proxy"] = proxy

        assert self._pw is not None, "Playwright failed to start"
        self._browser = await self._pw.chromium.launch(**launch_kwargs)

        # L2: Build context kwargs from persona
        context_kwargs: dict[str, Any] = {
            "accept_downloads": True,
        }

        if self._persona:
            context_kwargs["user_agent"] = self._persona.user_agent
            context_kwargs["viewport"] = {
                "width": self._persona.viewport_width,
                "height": self._persona.viewport_height,
            }
            context_kwargs["screen"] = {
                "width": self._persona.screen_width,
                "height": self._persona.screen_height,
            }
            context_kwargs["locale"] = self._persona.locale
            context_kwargs["timezone_id"] = self._persona.timezone_id
            if self._persona.http_headers:
                context_kwargs["extra_http_headers"] = self._persona.http_headers
        else:
            context_kwargs["locale"] = self._settings.locale

        if self._storage_state and self._storage_state.exists():
            context_kwargs["storage_state"] = str(self._storage_state)

        self._context = await self._browser.new_context(**context_kwargs)
        self._context.set_default_navigation_timeout(self._settings.navigation_timeout_ms)
        self._context.set_default_timeout(self._settings.action_timeout_ms)
        return BrowserSession(self._pw, self._browser, self._context)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Best-effort cleanup (reverse creation order)
        try:
            if self._context is not None:
                await self._context.close()
        finally:
            try:
                if self._browser is not None:
                    await self._browser.close()
            finally:
                if self._stealth_cm is not None:
                    await self._stealth_cm.__aexit__(exc_type, exc, tb)


@asynccontextmanager
async def with_browser(
    settings: Settings,
    *,
    storage_state: Path | None = None,
    persona: Persona | None = None,
) -> AsyncIterator[BrowserSession]:
    """Create a stealth browser session with fingerprint injection.

    This is the low-level helper.  Prefer the SessionManager-aware
    ``with_session_browser()`` for production crawlers.
    """
    async with BrowserManager(
        settings,
        storage_state=storage_state,
        persona=persona,
    ) as session:
        yield session


@asynccontextmanager
async def with_session_browser(
    settings: Settings,
    *,
    site_name: str,
    force_new_persona: bool = False,
) -> AsyncIterator[BrowserSession]:
    """Create a stealth browser session backed by ``SessionManager``.

    Automatically loads storage-state, persona, and bumps ``last_used_at``.
    """
    from wine_crawler.core.session import SessionManager

    sm = SessionManager(settings, site_name)
    sm.migrate_legacy()

    persona = sm.get_or_create_persona(force_new=force_new_persona)
    storage = sm.state_path if sm.state_path.exists() else None

    async with BrowserManager(
        settings,
        storage_state=storage,
        persona=persona,
    ) as session:
        sm.touch()
        yield session
