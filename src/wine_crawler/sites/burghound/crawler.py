"""Burghound.com -- login + crawl, using stealth infrastructure.

Conforms to the ``SiteCrawler`` ABC so it can be registered in the site
registry and driven by the shared CLI.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from wine_crawler.core.human import (
    human_click,
    human_delay,
    human_type,
    medium_pause,
    short_pause,
)
from wine_crawler.core.session import SessionManager
from wine_crawler.core.types import CrawlResult
from wine_crawler.sites.base import SiteCrawler

if TYPE_CHECKING:
    from logging import Logger

    from playwright.async_api import Page

    from wine_crawler.config import Settings
    from wine_crawler.core.browser import BrowserSession


class BurghoundCrawler(SiteCrawler):
    """Burghound.com site crawler."""

    name = "burghound"

    BASE_URL = "https://www.burghound.com/tnsearch/index.php"

    # ------------------------------------------------------------------
    # SiteCrawler interface
    # ------------------------------------------------------------------

    async def crawl(
        self,
        *,
        settings: Settings,
        session: BrowserSession,
        logger: Logger,
        limit: int,
    ) -> CrawlResult:
        """Login (if needed) then crawl."""
        email = settings.burghound_email
        password = settings.burghound_password
        if not email or not password:
            raise RuntimeError(
                "Burghound credentials not set. Set BURGHOUND_EMAIL and BURGHOUND_PASSWORD in .env"
            )

        sm = SessionManager(settings, self.name)

        # Attempt login
        logged_in = await self._login(
            session,
            email=email,
            password=password,
            logger=logger,
            settings=settings,
            session_mgr=sm,
        )
        if not logged_in:
            raise RuntimeError("Failed to log in to Burghound.com")

        # TODO: implement actual search/scrape logic below
        try:
            page = await session.context.new_page()
            try:
                _ = await page.goto(self.BASE_URL)
                await page.wait_for_load_state("networkidle")
                await medium_pause()

                items: list[dict[str, Any]] = []
                meta: dict[str, Any] = {
                    "site": self.name,
                    "url": self.BASE_URL,
                    "logged_in": True,
                }
                return CrawlResult(items=items, meta=meta)
            finally:
                await page.close()
        finally:
            # ALWAYS logout to avoid 1-hour account lockout
            logger.info("Logging out to release server session…")
            _ = await self._logout(session, logger=logger, session_mgr=sm)

    # ------------------------------------------------------------------
    # Login helpers (standalone, also callable from CLI ``login`` command)
    # ------------------------------------------------------------------

    async def _login(
        self,
        session: BrowserSession,
        *,
        email: str,
        password: str,
        logger: Logger,
        settings: Settings | None = None,
        session_mgr: SessionManager | None = None,
        force: bool = False,
    ) -> bool:
        """Perform a human-like login to Burghound.com.

        Returns True on success.
        """
        # Quick check: are we already logged in?
        if not force and await self._is_logged_in(session, logger=logger):
            logger.info("Already logged in (session still valid)")
            if session_mgr:
                _ = session_mgr.touch()
            return True

        page = await session.context.new_page()
        try:
            logger.info("Navigating to %s", self.BASE_URL)
            _ = await page.goto(self.BASE_URL)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(base=2.0, sigma=0.5)

            # -- dismiss cookie banner -----------------------------------
            await self._dismiss_cookie_banner(page, logger=logger)

            # -- dismiss modal dialogs -----------------------------------
            await self._dismiss_modals(page, logger=logger)

            # -- fill email ----------------------------------------------
            email_el = await self._find_email_input(page)
            if email_el is None:
                logger.error("Could not locate email input")
                return False

            logger.info("Typing email")
            await human_type(page, email_el, email)
            await medium_pause()

            # -- fill password -------------------------------------------
            password_el = page.locator('input[type="password"]').first
            if not await password_el.is_visible(timeout=5000):
                logger.error("Could not locate password input")
                return False

            logger.info("Typing password")
            await human_type(page, password_el, password)
            await medium_pause()

            # -- click Sign In -------------------------------------------
            sign_in = await self._find_sign_in_button(page)
            if sign_in is None:
                logger.error("Could not locate Sign In button")
                return False

            logger.info("Clicking Sign In")
            await sign_in.scroll_into_view_if_needed()
            await short_pause()
            await human_click(page, sign_in)

            # -- wait for response ---------------------------------------
            try:
                await page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception:
                await asyncio.sleep(3)
            await human_delay(base=2.0, sigma=0.5)

            # Debug: capture post-login state
            logger.info("Post-login URL: %s", page.url)
            if settings:
                try:
                    ss_dir = settings.screenshots_dir
                    ss_dir.mkdir(parents=True, exist_ok=True)
                    _ = await page.screenshot(path=str(ss_dir / "post_login.png"))
                except Exception:
                    pass

            # -- check for account lockout --------------------------------
            if await self._is_account_locked(page):
                logger.error(
                    ("Account locked: previous session was not logged out. "
                     "Wait ~1 hour or log out from another browser.")
                )
                if session_mgr:
                    session_mgr.mark_expired()
                return False

            # -- verify success ------------------------------------------
            if await self._has_login_error(page):
                logger.error("Login failed (error message on page)")
                if session_mgr:
                    session_mgr.mark_expired()
                return False

            # Check if we're still on the login page
            still_on_login = await page.locator('input[type="password"]').count() > 0
            if still_on_login and "index.php" in page.url:
                logger.error("Login failed (still on login page, url=%s)", page.url)
                if session_mgr:
                    session_mgr.mark_expired()
                return False

            logger.info("Login successful")

            # -- persist session -----------------------------------------
            if session_mgr:
                _ = await session.context.storage_state(path=str(session_mgr.state_path))
                ua = ""
                persona = session_mgr.load_persona()
                if persona:
                    ua = persona.user_agent
                _ = session_mgr.mark_login(user_agent=ua)
                logger.info("Session saved to %s", session_mgr.session_dir)

            return True

        except Exception:
            logger.exception("Login error")
            return False
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def _logout(
        self,
        session: BrowserSession,
        *,
        logger: Logger,
        session_mgr: SessionManager | None = None,
    ) -> bool:
        """Explicitly log out of Burghound.com to release the server-side session.

        Burghound locks the account for 1 hour if you don't log out properly.
        This clicks the "DATABASE LOGOUT" button.

        Returns True if logout succeeded (or we weren't logged in).
        """
        page = await session.context.new_page()
        try:
            _ = await page.goto(self.BASE_URL)
            await page.wait_for_load_state("networkidle", timeout=12_000)
            await human_delay(base=1.0, sigma=0.3)

            # Look for the LOGOUT button/link
            logout_selectors = [
                'a:has-text("DATABASE LOGOUT")',
                'a:has-text("LOGOUT")',
                'button:has-text("LOGOUT")',
                'a[href*="logout" i]',
                ':text("DATABASE LOGOUT")',
            ]

            for sel in logout_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        logger.info("Clicking logout: %s", sel)
                        await human_click(page, btn)

                        # Wait for the logout to complete
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10_000)
                        except Exception:
                            await asyncio.sleep(2)
                        await human_delay(base=1.0, sigma=0.3)

                        logger.info("Logout successful")
                        if session_mgr:
                            _ = session_mgr.mark_logout()
                        return True
                except Exception:
                    continue

            # If we're already on the login page, we're not logged in
            has_login_form = (
                await page.locator('input[type="email"], input[type="password"]').count() > 0
            )
            if has_login_form:
                logger.info("Not logged in, no logout needed")
                return True

            logger.warning("Could not find logout button")
            return False

        except Exception:
            logger.exception("Logout error")
            return False
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _is_logged_in(self, session: BrowserSession, *, logger: Logger) -> bool:
        """Open the login page and check whether we're already authenticated."""
        page = await session.context.new_page()
        try:
            _ = await page.goto(self.BASE_URL)
            await page.wait_for_load_state("networkidle", timeout=12_000)
            await human_delay(base=1.5, sigma=0.3)

            has_login_form = (
                await page.locator('input[type="email"], input[type="password"]').count() > 0
            )
            return not has_login_form
        except Exception:
            return False
        finally:
            await page.close()

    @staticmethod
    async def _dismiss_cookie_banner(page: Page, *, logger: Logger) -> None:
        try:
            btn = page.locator("text=ACCEPT").first
            if await btn.is_visible(timeout=3000):
                await human_click(page, btn)
                logger.debug("Dismissed cookie banner")
                await short_pause()
        except Exception:
            pass

    @staticmethod
    async def _dismiss_modals(page: Page, *, logger: Logger) -> None:
        """Close any overlay / instruction-download modals and notification bars."""
        close_selectors = [
            "button.close",
            '[aria-label="Close"]',
            'button:has-text("\u00d7")',
            ".close",
            "span.close",
            "a.close",
        ]
        for sel in close_selectors:
            try:
                buttons = page.locator(sel)
                count = await buttons.count()
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible(timeout=1000):
                        await btn.click(force=True)
                        logger.debug("Dismissed modal (%s, #%d)", sel, i)
                        await short_pause()
            except Exception:
                continue

        try:
            all_close = page.locator(':text-is("\u00d7")')
            count = await all_close.count()
            for i in range(count):
                btn = all_close.nth(i)
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True)
                    await short_pause()
        except Exception:
            pass

    @staticmethod
    async def _find_email_input(page: Page) -> Any:
        selectors = [
            'input[type="email"]',
            'input[name*="email" i]',
            'input[id*="email" i]',
            'input[placeholder*="Email" i]',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    return el
            except Exception:
                continue
        return None

    @staticmethod
    async def _find_sign_in_button(page: Page) -> Any:
        selectors = [
            'button:has-text("Sign In")',
            'input[type="submit"][value*="Sign" i]',
            'button[type="submit"]',
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    return el
            except Exception:
                continue
        return None

    @staticmethod
    async def _has_login_error(page: Page) -> bool:
        error_selectors = [".error", ".alert-danger", "text=/incorrect/i", "text=/invalid/i"]
        for sel in error_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    async def _is_account_locked(page: Page) -> bool:
        """Detect the 'Account in use' lockout page.

        Burghound locks the account for 1 hour if the previous session
        wasn't explicitly logged out.
        """
        lock_selectors = [
            "text=/Account in use/i",
            "text=/forgot to log out/i",
            "text=/unable to sign in/i",
        ]
        for sel in lock_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    return True
            except Exception:
                continue
        return False
