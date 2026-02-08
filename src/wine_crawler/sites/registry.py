from __future__ import annotations

from typing import TYPE_CHECKING

from wine_crawler.sites.burghound.crawler import BurghoundCrawler
from wine_crawler.sites.example.crawler import ExampleCrawler

if TYPE_CHECKING:
    from collections.abc import Callable

    from wine_crawler.sites.base import SiteCrawler

_FACTORIES: dict[str, Callable[[], SiteCrawler]] = {
    "burghound": BurghoundCrawler,
    "example": ExampleCrawler,
}


def list_sites() -> list[str]:
    return sorted(_FACTORIES.keys())


def get_crawler(site_name: str) -> SiteCrawler:
    try:
        return _FACTORIES[site_name]()
    except KeyError as e:
        raise KeyError(f"Unknown site: {site_name}. Available: {', '.join(list_sites())}") from e
