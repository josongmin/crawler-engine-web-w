from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import Logger

    from wine_crawler.config import Settings
    from wine_crawler.core import BrowserSession, CrawlResult


class SiteCrawler(ABC):
    name: str

    @abstractmethod
    async def crawl(
        self,
        *,
        settings: Settings,
        session: BrowserSession,
        logger: Logger,
        limit: int,
    ) -> CrawlResult: ...
