from __future__ import annotations

from wine_crawler.sites import get_crawler, list_sites


def test_list_sites_contains_example() -> None:
    assert "example" in list_sites()


def test_get_crawler_returns_named_instance() -> None:
    crawler = get_crawler("example")
    assert crawler.name == "example"
