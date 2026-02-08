"""Pydantic domain models for the admin database.

Each model mirrors a database table with strict typing.  ``*Create`` models
are used for inserts (no auto-generated fields), the main model is used for
reads.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def utcnow() -> str:
    """ISO-8601 UTC timestamp string."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------


class Project(BaseModel):
    id: str
    name: str
    site: str
    description: str | None = None
    status: str = "active"
    created_at: str
    updated_at: str


class ProjectCreate(BaseModel):
    name: str
    site: str
    description: str | None = None
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str | None = None
    site: str | None = None
    description: str | None = None
    status: str | None = None


# ------------------------------------------------------------------
# Crawl Rules
# ------------------------------------------------------------------


class CrawlRule(BaseModel):
    id: str
    project_id: str
    name: str
    page_type: str
    url_pattern: str | None = None
    version: int = 1
    rule_body: str  # JSON string
    is_active: bool = True
    created_at: str
    updated_at: str
    created_by: str = "admin"


class CrawlRuleCreate(BaseModel):
    project_id: str
    name: str
    page_type: str
    url_pattern: str | None = None
    rule_body: str
    created_by: str = "admin"


class CrawlRuleUpdate(BaseModel):
    name: str | None = None
    page_type: str | None = None
    url_pattern: str | None = None
    rule_body: str | None = None
    is_active: bool | None = None


# ------------------------------------------------------------------
# Jobs
# ------------------------------------------------------------------


class Job(BaseModel):
    id: str
    project_id: str | None = None
    site: str
    rule_id: str | None = None
    executor: str = "local"
    executor_meta: str | None = None  # JSON string
    status: str = "pending"
    limit_n: int = 10
    headless: bool = True
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    item_count: int = 0
    error: str | None = None
    output_path: str | None = None
    meta: str | None = None  # JSON string


class JobCreate(BaseModel):
    site: str
    project_id: str | None = None
    rule_id: str | None = None
    executor: str = "local"
    executor_meta: str | None = None
    limit_n: int = 10
    headless: bool = True
    meta: str | None = None


class JobUpdate(BaseModel):
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    item_count: int | None = None
    error: str | None = None
    output_path: str | None = None


# ------------------------------------------------------------------
# Job Logs
# ------------------------------------------------------------------


class JobLog(BaseModel):
    id: int
    job_id: str
    level: str
    message: str
    timestamp: str
    source: str | None = None


class JobLogCreate(BaseModel):
    job_id: str
    level: str
    message: str
    source: str | None = None


# ------------------------------------------------------------------
# Credentials
# ------------------------------------------------------------------


class Credential(BaseModel):
    site: str
    email: str
    password_enc: str
    notes: str | None = None
    updated_at: str


class CredentialUpsert(BaseModel):
    site: str
    email: str
    password_enc: str
    notes: str | None = None


# ------------------------------------------------------------------
# Schedules
# ------------------------------------------------------------------


class Schedule(BaseModel):
    id: str
    site: str
    project_id: str | None = None
    rule_id: str | None = None
    cron_expr: str
    limit_n: int = 10
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None
    created_at: str


class ScheduleCreate(BaseModel):
    site: str
    project_id: str | None = None
    rule_id: str | None = None
    cron_expr: str
    limit_n: int = 10
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    cron_expr: str | None = None
    limit_n: int | None = None
    enabled: bool | None = None
    last_run: str | None = None
    next_run: str | None = None


# ------------------------------------------------------------------
# Request Kits
# ------------------------------------------------------------------


class RequestKit(BaseModel):
    id: str
    site: str
    format: str
    snippet_enc: str
    cookies_enc: str
    headers_enc: str | None = None
    csrf_extractor: str | None = None  # JSON string
    user_agent: str | None = None
    expires_at: str | None = None
    created_at: str
    used_count: int = 0
    last_used: str | None = None
    notes: str | None = None


class RequestKitCreate(BaseModel):
    site: str
    format: str
    snippet_enc: str
    cookies_enc: str
    headers_enc: str | None = None
    csrf_extractor: str | None = None
    user_agent: str | None = None
    expires_at: str | None = None
    notes: str | None = None


# ------------------------------------------------------------------
# Site Capabilities
# ------------------------------------------------------------------


class SiteCapability(BaseModel):
    site: str
    supports_request_kit: bool = True
    logout_strategy: str  # JSON string
    login_validator: str  # JSON string
    token_validator: str  # JSON string
    csrf_required: bool = False
    csrf_source: str | None = None
    csrf_key: str | None = None
    updated_at: str


class SiteCapabilityUpsert(BaseModel):
    site: str
    supports_request_kit: bool = True
    logout_strategy: str
    login_validator: str
    token_validator: str
    csrf_required: bool = False
    csrf_source: str | None = None
    csrf_key: str | None = None


# ------------------------------------------------------------------
# Rule Versions
# ------------------------------------------------------------------


class RuleVersion(BaseModel):
    id: int
    rule_id: str
    version: int
    rule_body: str
    change_note: str | None = None
    created_at: str


class RuleVersionCreate(BaseModel):
    rule_id: str
    version: int
    rule_body: str
    change_note: str | None = None


# ------------------------------------------------------------------
# Rule Test Results
# ------------------------------------------------------------------


class RuleTestResult(BaseModel):
    id: str
    rule_id: str
    test_url: str
    status: str
    extracted: str | None = None  # JSON string
    errors: str | None = None  # JSON string
    screenshot: str | None = None
    duration_ms: int | None = None
    created_at: str


class RuleTestResultCreate(BaseModel):
    rule_id: str
    test_url: str
    status: str
    extracted: str | None = None
    errors: str | None = None
    screenshot: str | None = None
    duration_ms: int | None = None


# ------------------------------------------------------------------
# KV Store
# ------------------------------------------------------------------


class KVEntry(BaseModel):
    key: str
    value: str
