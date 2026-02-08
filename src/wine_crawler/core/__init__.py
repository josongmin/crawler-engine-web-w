from __future__ import annotations

from wine_crawler.core.browser import (
    BrowserManager,
    BrowserSession,
    with_browser,
)
from wine_crawler.core.fingerprint import Persona, generate_persona, get_or_create_persona
from wine_crawler.core.human import human_click, human_delay, human_type, medium_pause, short_pause
from wine_crawler.core.retry import default_retry
from wine_crawler.core.session import SessionManager, SessionMeta, list_sessions
from wine_crawler.core.types import CrawlResult

__all__ = [
    "BrowserManager",
    "BrowserSession",
    "CrawlResult",
    "Persona",
    "SessionManager",
    "SessionMeta",
    "default_retry",
    "generate_persona",
    "get_or_create_persona",
    "human_click",
    "human_delay",
    "human_type",
    "list_sessions",
    "medium_pause",
    "short_pause",
    "with_browser",
]
