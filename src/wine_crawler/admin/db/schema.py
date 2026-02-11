"""Versioned schema migrations for admin.db.

Each migration is a ``(version, description, sql)`` tuple. Migrations are
applied in order; the current version is tracked in ``_schema_version``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wine_crawler.admin.db.connection import Database

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Migration 1: Initial schema
# ------------------------------------------------------------------

_V1_SQL = """\
-- =============================================
-- Internal: schema version tracking
-- =============================================

CREATE TABLE IF NOT EXISTS _schema_version (
    version     INTEGER PRIMARY KEY,
    description TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- =============================================
-- Core Tables
-- =============================================

CREATE TABLE projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    site        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE crawl_rules (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    page_type   TEXT NOT NULL,
    url_pattern TEXT,
    version     INTEGER NOT NULL DEFAULT 1,
    rule_body   TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT 'admin'
);

CREATE TABLE jobs (
    id            TEXT PRIMARY KEY,
    project_id    TEXT REFERENCES projects(id) ON DELETE SET NULL,
    site          TEXT NOT NULL,
    rule_id       TEXT REFERENCES crawl_rules(id) ON DELETE SET NULL,
    executor      TEXT NOT NULL DEFAULT 'local',
    executor_meta TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',
    limit_n       INTEGER NOT NULL DEFAULT 10,
    headless      INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT,
    duration_ms   INTEGER,
    item_count    INTEGER NOT NULL DEFAULT 0,
    error         TEXT,
    output_path   TEXT,
    meta          TEXT
);

CREATE TABLE job_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT    NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    level      TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    timestamp  TEXT    NOT NULL,
    source     TEXT
);

CREATE TABLE credentials (
    site         TEXT PRIMARY KEY,
    email        TEXT NOT NULL,
    password_enc TEXT NOT NULL,
    notes        TEXT,
    updated_at   TEXT NOT NULL
);

CREATE TABLE schedules (
    id         TEXT PRIMARY KEY,
    site       TEXT NOT NULL,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    rule_id    TEXT REFERENCES crawl_rules(id) ON DELETE SET NULL,
    cron_expr  TEXT NOT NULL,
    limit_n    INTEGER NOT NULL DEFAULT 10,
    enabled    INTEGER NOT NULL DEFAULT 1,
    last_run   TEXT,
    next_run   TEXT,
    created_at TEXT NOT NULL
);

-- =============================================
-- Request Kit Export
-- =============================================

CREATE TABLE request_kits (
    id              TEXT PRIMARY KEY,
    site            TEXT NOT NULL,
    format          TEXT NOT NULL,
    snippet_enc     TEXT NOT NULL,
    cookies_enc     TEXT NOT NULL,
    headers_enc     TEXT,
    csrf_extractor  TEXT,
    user_agent      TEXT,
    expires_at      TEXT,
    created_at      TEXT NOT NULL,
    used_count      INTEGER NOT NULL DEFAULT 0,
    last_used       TEXT,
    notes           TEXT
);

-- =============================================
-- Site Capabilities
-- =============================================

CREATE TABLE site_capabilities (
    site                 TEXT PRIMARY KEY,
    supports_request_kit INTEGER NOT NULL DEFAULT 1,
    logout_strategy      TEXT    NOT NULL,
    login_validator      TEXT    NOT NULL,
    token_validator      TEXT    NOT NULL,
    csrf_required        INTEGER NOT NULL DEFAULT 0,
    csrf_source          TEXT,
    csrf_key             TEXT,
    updated_at           TEXT    NOT NULL
);

-- =============================================
-- Rule Versions & Test Results
-- =============================================

CREATE TABLE rule_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id     TEXT    NOT NULL REFERENCES crawl_rules(id) ON DELETE CASCADE,
    version     INTEGER NOT NULL,
    rule_body   TEXT    NOT NULL,
    change_note TEXT,
    created_at  TEXT    NOT NULL,
    UNIQUE(rule_id, version)
);

CREATE TABLE rule_test_results (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT    NOT NULL REFERENCES crawl_rules(id) ON DELETE CASCADE,
    test_url    TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    extracted   TEXT,
    errors      TEXT,
    screenshot  TEXT,
    duration_ms INTEGER,
    created_at  TEXT    NOT NULL
);

-- =============================================
-- KV Store (settings, state)
-- =============================================

CREATE TABLE kv_store (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- =============================================
-- Indexes
-- =============================================

CREATE INDEX idx_jobs_site       ON jobs(site);
CREATE INDEX idx_jobs_status     ON jobs(status);
CREATE INDEX idx_jobs_project_id ON jobs(project_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

CREATE INDEX idx_job_logs_job_id    ON job_logs(job_id);
CREATE INDEX idx_job_logs_timestamp ON job_logs(timestamp);

CREATE INDEX idx_request_kits_site       ON request_kits(site);
CREATE INDEX idx_request_kits_created_at ON request_kits(created_at);

CREATE INDEX idx_crawl_rules_project_id ON crawl_rules(project_id);
CREATE INDEX idx_crawl_rules_page_type  ON crawl_rules(page_type);

CREATE INDEX idx_rule_versions_rule_id     ON rule_versions(rule_id);
CREATE INDEX idx_rule_test_results_rule_id ON rule_test_results(rule_id);

CREATE INDEX idx_schedules_site       ON schedules(site);
CREATE INDEX idx_schedules_project_id ON schedules(project_id);
CREATE INDEX idx_schedules_enabled    ON schedules(enabled);
"""

# ------------------------------------------------------------------
# Migration registry
# ------------------------------------------------------------------

Migration = tuple[int, str, str]

_V2_SQL = """\
-- =============================================
-- Workflows
-- =============================================

CREATE TABLE workflows (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    site            TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    graph_json      TEXT NOT NULL,
    compiled_json   TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX idx_workflows_site   ON workflows(site);
CREATE INDEX idx_workflows_status ON workflows(status);

-- =============================================
-- Workflow Runs
-- =============================================

CREATE TABLE workflow_runs (
    id               TEXT PRIMARY KEY,
    workflow_id      TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    status           TEXT NOT NULL DEFAULT 'pending',
    node_states_json TEXT,
    started_at       TEXT,
    finished_at      TEXT,
    duration_ms      INTEGER,
    error            TEXT,
    created_at       TEXT NOT NULL
);

CREATE INDEX idx_workflow_runs_workflow_id ON workflow_runs(workflow_id);
CREATE INDEX idx_workflow_runs_status      ON workflow_runs(status);
CREATE INDEX idx_workflow_runs_created_at  ON workflow_runs(created_at);

-- =============================================
-- Workflow Node Logs
-- =============================================

CREATE TABLE workflow_node_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    node_id     TEXT NOT NULL,
    level       TEXT NOT NULL,
    message     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    data_json   TEXT
);

CREATE INDEX idx_wf_node_logs_run_id    ON workflow_node_logs(run_id);
CREATE INDEX idx_wf_node_logs_node_id   ON workflow_node_logs(node_id);
CREATE INDEX idx_wf_node_logs_timestamp ON workflow_node_logs(timestamp);
"""

MIGRATIONS: Sequence[Migration] = [
    (1, "initial schema", _V1_SQL),
    (2, "workflow engine tables", _V2_SQL),
]


# ------------------------------------------------------------------
# Migration runner
# ------------------------------------------------------------------


async def apply_migrations(db: Database) -> None:
    """Apply any pending migrations in order."""
    # Ensure the version table exists (idempotent)
    _ = await db.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    await db.connection.commit()

    current = await db.fetch_val("SELECT MAX(version) FROM _schema_version")
    current = current or 0

    for version, description, sql in MIGRATIONS:
        if version <= current:
            continue
        logger.info("Applying migration v%d: %s", version, description)
        _ = await db.connection.executescript(sql)
        _ = await db.connection.execute(
            "INSERT INTO _schema_version (version, description) VALUES (?, ?)",
            [version, description],
        )
        await db.connection.commit()
        logger.info("Migration v%d applied successfully", version)

    final = await db.fetch_val("SELECT MAX(version) FROM _schema_version")
    logger.info("Schema version: %d", final or 0)
