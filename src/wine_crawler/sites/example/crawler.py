from __future__ import annotations

from typing import TYPE_CHECKING

from wine_crawler.core import BrowserSession, CrawlResult
from wine_crawler.sites.base import SiteCrawler

if TYPE_CHECKING:
    from logging import Logger

    from playwright.async_api import Page

    from wine_crawler.config import Settings


class ExampleCrawler(SiteCrawler):
    name = "example"

    async def crawl(
        self,
        *,
        settings: Settings,
        session: BrowserSession,
        logger: Logger,
        limit: int,
    ) -> CrawlResult:
        # Minimal smoke-test crawler (replace with real per-site logic)
        page: Page = await session.context.new_page()
        try:
            url = "https://example.com/"
            logger.info("Navigating to %s", url)
            _ = await page.goto(url, wait_until="domcontentloaded")

            title = await page.title()
            h1 = await page.locator("h1").first.text_content()

            item = {
                "url": url,
                "title": title,
                "h1": (h1 or "").strip(),
            }
            safe_limit = max(limit, 0)
            return CrawlResult(items=[item][:safe_limit], meta={"site": self.name})
        finally:
            await page.close()
