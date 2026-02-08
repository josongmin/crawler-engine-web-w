"""Repository classes for each domain entity."""

from __future__ import annotations

from wine_crawler.admin.db.repositories.base import BaseRepository
from wine_crawler.admin.db.repositories.crawl_rules import CrawlRulesRepository
from wine_crawler.admin.db.repositories.credentials import CredentialsRepository
from wine_crawler.admin.db.repositories.job_logs import JobLogsRepository
from wine_crawler.admin.db.repositories.jobs import JobsRepository
from wine_crawler.admin.db.repositories.kv_store import KVStoreRepository
from wine_crawler.admin.db.repositories.projects import ProjectsRepository
from wine_crawler.admin.db.repositories.request_kits import RequestKitsRepository
from wine_crawler.admin.db.repositories.rule_test_results import RuleTestResultsRepository
from wine_crawler.admin.db.repositories.rule_versions import RuleVersionsRepository
from wine_crawler.admin.db.repositories.schedules import SchedulesRepository
from wine_crawler.admin.db.repositories.site_capabilities import SiteCapabilitiesRepository

__all__ = [
    "BaseRepository",
    "CrawlRulesRepository",
    "CredentialsRepository",
    "JobLogsRepository",
    "JobsRepository",
    "KVStoreRepository",
    "ProjectsRepository",
    "RequestKitsRepository",
    "RuleTestResultsRepository",
    "RuleVersionsRepository",
    "SchedulesRepository",
    "SiteCapabilitiesRepository",
]
