"""Site-specific crawlers."""

from __future__ import annotations

from wine_crawler.sites.base import SiteCrawler
from wine_crawler.sites.registry import get_crawler, list_sites

__all__ = ["SiteCrawler", "get_crawler", "list_sites"]
