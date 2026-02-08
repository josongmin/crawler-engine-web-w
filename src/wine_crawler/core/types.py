from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CrawlResult:
    items: list[dict[str, Any]]
    meta: dict[str, Any]
