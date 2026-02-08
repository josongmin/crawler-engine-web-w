"""Tests for the admin SQLite database layer.

Covers: connection lifecycle, schema migrations, all repositories CRUD,
FK cascade, constraint violations, edge cases, and full lifecycle flows.
Each test gets a fresh temp-file database via the ``db`` fixture.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import aiosqlite
import pytest

from wine_crawler.admin.db.connection import Database
from wine_crawler.admin.db.models import (
    CrawlRuleCreate,
    CrawlRuleUpdate,
    CredentialUpsert,
    JobCreate,
    JobLogCreate,
    ProjectCreate,
    ProjectUpdate,
    RequestKitCreate,
    RuleTestResultCreate,
    RuleVersionCreate,
    ScheduleCreate,
    ScheduleUpdate,
    SiteCapabilityUpsert,
)

if TYPE_CHECKING:
    from pathlib import Path


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    """Yield a connected Database backed by a temp file (for WAL support)."""
    db = Database(tmp_path / "test_admin.db")
    await db.connect()
    yield db  # type: ignore[misc]
    await db.disconnect()


# ------------------------------------------------------------------
# Connection & Schema
# ------------------------------------------------------------------


class TestConnection:
    async def test_connect_creates_file(self, tmp_path: Path) -> None:
        db_path = tmp_path / "new.db"
        async with Database(db_path):
            assert db_path.exists()

    async def test_connect_creates_parent_dirs(self, tmp_path: Path) -> None:
        db_path = tmp_path / "nested" / "deep" / "admin.db"
        async with Database(db_path):
            assert db_path.exists()

    async def test_double_connect_is_safe(self, db: Database) -> None:
        await db.connect()  # should not raise

    async def test_disconnect_and_reconnect(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "reconnect.db")
        await db.connect()
        await db.disconnect()
        await db.connect()
        row = await db.fetch_one("SELECT 1 AS val")
        assert row is not None and row["val"] == 1
        await db.disconnect()

    async def test_double_disconnect_is_safe(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "safe_dc.db")
        await db.connect()
        await db.disconnect()
        await db.disconnect()  # should not raise

    async def test_connection_property_raises_when_disconnected(
        self, tmp_path: Path
    ) -> None:
        db = Database(tmp_path / "disconnected.db")
        with pytest.raises(RuntimeError, match="not connected"):
            _ = db.connection

    async def test_fetch_one_returns_dict(self, db: Database) -> None:
        row = await db.fetch_one("SELECT 1 AS a, 'hello' AS b")
        assert row == {"a": 1, "b": "hello"}

    async def test_fetch_one_returns_none_for_no_match(self, db: Database) -> None:
        row = await db.fetch_one("SELECT * FROM projects WHERE id = 'nonexistent'")
        assert row is None

    async def test_fetch_all(self, db: Database) -> None:
        rows = await db.fetch_all("SELECT 1 AS v UNION ALL SELECT 2")
        assert len(rows) == 2

    async def test_fetch_all_empty(self, db: Database) -> None:
        rows = await db.fetch_all("SELECT * FROM projects")
        assert rows == []

    async def test_fetch_val_scalar(self, db: Database) -> None:
        val = await db.fetch_val("SELECT 42")
        assert val == 42

    async def test_fetch_val_none(self, db: Database) -> None:
        val = await db.fetch_val(
            "SELECT id FROM projects WHERE id = 'nonexistent'"
        )
        assert val is None

    async def test_execute_many(self, db: Database) -> None:
        await db.execute_many(
            "INSERT INTO kv_store (key, value) VALUES (?, ?)",
            [["k1", "v1"], ["k2", "v2"], ["k3", "v3"]],
        )
        count = await db.fetch_val("SELECT COUNT(*) FROM kv_store")
        assert count == 3

    async def test_transaction_commit(self, db: Database) -> None:
        async with db.transaction():
            await db.connection.execute(
                "INSERT INTO kv_store (key, value) VALUES (?, ?)",
                ["tx_key", "tx_val"],
            )
        row = await db.fetch_one("SELECT value FROM kv_store WHERE key = 'tx_key'")
        assert row is not None and row["value"] == "tx_val"

    async def test_transaction_rollback(self, db: Database) -> None:
        with pytest.raises(ValueError, match="force rollback"):
            async with db.transaction():
                await db.connection.execute(
                    "INSERT INTO kv_store (key, value) VALUES (?, ?)",
                    ["rollback_key", "oops"],
                )
                raise ValueError("force rollback")
        row = await db.fetch_one(
            "SELECT value FROM kv_store WHERE key = 'rollback_key'"
        )
        assert row is None

    async def test_repos_property_lazy_init(self, db: Database) -> None:
        r1 = db.repos
        r2 = db.repos
        assert r1 is r2  # same instance


class TestSchema:
    async def test_schema_version_exists(self, db: Database) -> None:
        version = await db.fetch_val("SELECT MAX(version) FROM _schema_version")
        assert version == 1

    async def test_migration_has_description(self, db: Database) -> None:
        row = await db.fetch_one(
            "SELECT description, applied_at FROM _schema_version WHERE version = 1"
        )
        assert row is not None
        assert row["description"] == "initial schema"
        assert row["applied_at"]  # non-empty timestamp

    async def test_all_tables_created(self, db: Database) -> None:
        rows = await db.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        table_names = {r["name"] for r in rows}
        expected = {
            "_schema_version",
            "projects",
            "crawl_rules",
            "jobs",
            "job_logs",
            "credentials",
            "schedules",
            "request_kits",
            "site_capabilities",
            "rule_versions",
            "rule_test_results",
            "kv_store",
        }
        assert expected.issubset(table_names)

    async def test_all_indexes_created(self, db: Database) -> None:
        rows = await db.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        index_names = {r["name"] for r in rows}
        expected_indexes = {
            "idx_jobs_site",
            "idx_jobs_status",
            "idx_jobs_project_id",
            "idx_jobs_created_at",
            "idx_job_logs_job_id",
            "idx_job_logs_timestamp",
            "idx_request_kits_site",
            "idx_request_kits_created_at",
            "idx_crawl_rules_project_id",
            "idx_crawl_rules_page_type",
            "idx_rule_versions_rule_id",
            "idx_rule_test_results_rule_id",
            "idx_schedules_site",
            "idx_schedules_project_id",
            "idx_schedules_enabled",
        }
        assert expected_indexes.issubset(index_names)

    async def test_foreign_keys_enabled(self, db: Database) -> None:
        val = await db.fetch_val("PRAGMA foreign_keys")
        assert val == 1

    async def test_wal_mode(self, db: Database) -> None:
        val = await db.fetch_val("PRAGMA journal_mode")
        assert val == "wal"

    async def test_idempotent_migration(self, db: Database) -> None:
        """Running migrations again should be a no-op."""
        from wine_crawler.admin.db.schema import apply_migrations

        await apply_migrations(db)
        version = await db.fetch_val("SELECT MAX(version) FROM _schema_version")
        assert version == 1
        # Only one row in _schema_version
        count = await db.fetch_val("SELECT COUNT(*) FROM _schema_version")
        assert count == 1


# ------------------------------------------------------------------
# Repository: Projects
# ------------------------------------------------------------------


class TestProjectsRepository:
    async def test_create_and_get(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="test-project", site="burghound")
        )
        assert project.name == "test-project"
        assert project.site == "burghound"
        assert project.status == "active"
        assert project.id  # non-empty UUID
        assert project.created_at
        assert project.updated_at

        fetched = await db.repos.projects.get(project.id)
        assert fetched is not None
        assert fetched.id == project.id

    async def test_get_nonexistent_returns_none(self, db: Database) -> None:
        assert await db.repos.projects.get("nonexistent-id") is None

    async def test_get_by_name(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="unique-name", site="burghound")
        )
        found = await db.repos.projects.get_by_name("unique-name")
        assert found is not None
        assert found.name == "unique-name"

    async def test_get_by_name_nonexistent(self, db: Database) -> None:
        assert await db.repos.projects.get_by_name("no-such-project") is None

    async def test_unique_name_constraint(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="dup-name", site="burghound")
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await db.repos.projects.create(
                ProjectCreate(name="dup-name", site="other")
            )

    async def test_update(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="to-update", site="burghound")
        )
        old_updated_at = project.updated_at

        updated = await db.repos.projects.update_project(
            project.id,
            ProjectUpdate(description="Updated description"),
        )
        assert updated is True
        fetched = await db.repos.projects.get(project.id)
        assert fetched is not None
        assert fetched.description == "Updated description"
        # updated_at should be refreshed
        assert fetched.updated_at >= old_updated_at

    async def test_update_empty_changes(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="no-change", site="burghound")
        )
        result = await db.repos.projects.update_project(
            project.id, ProjectUpdate()
        )
        assert result is False

    async def test_delete(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="to-delete", site="burghound")
        )
        deleted = await db.repos.projects.delete(project.id)
        assert deleted is True
        assert await db.repos.projects.get(project.id) is None

    async def test_delete_nonexistent(self, db: Database) -> None:
        result = await db.repos.projects.delete("nonexistent-id")
        assert result is False

    async def test_list_by_site(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="p1", site="burghound")
        )
        await db.repos.projects.create(
            ProjectCreate(name="p2", site="burghound")
        )
        await db.repos.projects.create(
            ProjectCreate(name="p3", site="other")
        )
        results = await db.repos.projects.list_by_site("burghound")
        assert len(results) == 2
        assert all(p.site == "burghound" for p in results)

    async def test_list_by_site_empty(self, db: Database) -> None:
        results = await db.repos.projects.list_by_site("nonexistent-site")
        assert results == []

    async def test_exists(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="exists-test", site="burghound")
        )
        assert await db.repos.projects.exists(project.id) is True
        assert await db.repos.projects.exists("nonexistent") is False

    async def test_count(self, db: Database) -> None:
        assert await db.repos.projects.count() == 0
        await db.repos.projects.create(
            ProjectCreate(name="c1", site="burghound")
        )
        await db.repos.projects.create(
            ProjectCreate(name="c2", site="burghound")
        )
        assert await db.repos.projects.count() == 2
        assert await db.repos.projects.count(site="burghound") == 2
        assert await db.repos.projects.count(site="other") == 0

    async def test_list_all_with_pagination(self, db: Database) -> None:
        for i in range(5):
            await db.repos.projects.create(
                ProjectCreate(name=f"pag-{i}", site="burghound")
            )
        page1 = await db.repos.projects.list_all(limit=3)
        assert len(page1) == 3
        page2 = await db.repos.projects.list_all(limit=3, offset=3)
        assert len(page2) == 2
        # No overlap
        ids1 = {p.id for p in page1}
        ids2 = {p.id for p in page2}
        assert ids1.isdisjoint(ids2)

    async def test_get_stats_empty(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="stats-empty", site="burghound")
        )
        stats = await db.repos.projects.get_stats(project.id)
        assert stats == {
            "rules_count": 0,
            "jobs_count": 0,
            "last_job_finished_at": None,
            "last_job_status": None,
        }

    async def test_get_stats_with_data(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="stats-data", site="burghound")
        )
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=project.id, name="r1",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=project.id, name="r2",
                page_type="detail", rule_body="{}",
            )
        )
        job = await db.repos.jobs.create(
            JobCreate(site="burghound", project_id=project.id)
        )
        await db.repos.jobs.update_status(job.id, "running")
        await db.repos.jobs.update_status(job.id, "completed", item_count=10)

        stats = await db.repos.projects.get_stats(project.id)
        assert stats["rules_count"] == 2
        assert stats["jobs_count"] == 1
        assert stats["last_job_status"] == "completed"
        assert stats["last_job_finished_at"] is not None


# ------------------------------------------------------------------
# Repository: Crawl Rules
# ------------------------------------------------------------------


class TestCrawlRulesRepository:
    async def _create_project(self, db: Database, name: str = "rule-project") -> str:
        p = await db.repos.projects.create(
            ProjectCreate(name=name, site="burghound")
        )
        return p.id

    async def test_create_and_get(self, db: Database) -> None:
        pid = await self._create_project(db)
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid,
                name="search-results",
                page_type="search",
                rule_body='{"extract": {}}',
            )
        )
        assert rule.name == "search-results"
        assert rule.version == 1
        assert rule.is_active is True
        assert rule.created_by == "admin"
        assert rule.project_id == pid

    async def test_create_with_custom_created_by(self, db: Database) -> None:
        pid = await self._create_project(db, "custom-creator-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="by-user", page_type="search",
                rule_body="{}", created_by="harry",
            )
        )
        assert rule.created_by == "harry"

    async def test_create_fk_violation(self, db: Database) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await db.repos.crawl_rules.create(
                CrawlRuleCreate(
                    project_id="nonexistent-project",
                    name="bad", page_type="search", rule_body="{}",
                )
            )

    async def test_bump_version(self, db: Database) -> None:
        pid = await self._create_project(db, "bump-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="v-test",
                page_type="search", rule_body='{"v": 1}',
            )
        )
        updated = await db.repos.crawl_rules.bump_version(rule.id, '{"v": 2}')
        assert updated is not None
        assert updated.version == 2
        assert updated.rule_body == '{"v": 2}'

    async def test_bump_version_nonexistent(self, db: Database) -> None:
        result = await db.repos.crawl_rules.bump_version("no-id", '{"v": 99}')
        assert result is None

    async def test_bump_version_multiple_times(self, db: Database) -> None:
        pid = await self._create_project(db, "multi-bump-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="multi-v",
                page_type="search", rule_body='{"v": 1}',
            )
        )
        for expected_v in range(2, 6):
            result = await db.repos.crawl_rules.bump_version(
                rule.id, json.dumps({"v": expected_v})
            )
            assert result is not None
            assert result.version == expected_v

    async def test_list_by_project(self, db: Database) -> None:
        pid = await self._create_project(db, "list-proj")
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="r1", page_type="search", rule_body="{}"
            )
        )
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="r2", page_type="detail", rule_body="{}"
            )
        )
        results = await db.repos.crawl_rules.list_by_project(pid)
        assert len(results) == 2

    async def test_list_by_project_active_only(self, db: Database) -> None:
        pid = await self._create_project(db, "active-filter-proj")
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="active", page_type="search", rule_body="{}"
            )
        )
        inactive_rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="inactive", page_type="detail", rule_body="{}"
            )
        )
        await db.repos.crawl_rules.update_rule(
            inactive_rule.id, CrawlRuleUpdate(is_active=False)
        )
        all_rules = await db.repos.crawl_rules.list_by_project(pid)
        assert len(all_rules) == 2
        active_rules = await db.repos.crawl_rules.list_by_project(
            pid, active_only=True
        )
        assert len(active_rules) == 1
        assert active_rules[0].name == "active"

    async def test_update_rule(self, db: Database) -> None:
        pid = await self._create_project(db, "upd-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="upd", page_type="search", rule_body="{}"
            )
        )
        await db.repos.crawl_rules.update_rule(
            rule.id,
            CrawlRuleUpdate(is_active=False),
        )
        fetched = await db.repos.crawl_rules.get(rule.id)
        assert fetched is not None
        assert fetched.is_active is False

    async def test_update_rule_empty_changes(self, db: Database) -> None:
        pid = await self._create_project(db, "empty-upd-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="empty-upd",
                page_type="search", rule_body="{}",
            )
        )
        result = await db.repos.crawl_rules.update_rule(
            rule.id, CrawlRuleUpdate()
        )
        assert result is False

    async def test_get_active_by_name(self, db: Database) -> None:
        pid = await self._create_project(db, "name-lookup-proj")
        await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="active-name",
                page_type="search", rule_body="{}",
            )
        )
        found = await db.repos.crawl_rules.get_active_by_name(pid, "active-name")
        assert found is not None

    async def test_get_active_by_name_returns_none_for_inactive(
        self, db: Database
    ) -> None:
        pid = await self._create_project(db, "inactive-lookup-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="now-inactive",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.crawl_rules.update_rule(
            rule.id, CrawlRuleUpdate(is_active=False)
        )
        found = await db.repos.crawl_rules.get_active_by_name(pid, "now-inactive")
        assert found is None

    async def test_get_active_by_name_nonexistent(self, db: Database) -> None:
        pid = await self._create_project(db, "noname-proj")
        assert await db.repos.crawl_rules.get_active_by_name(
            pid, "nonexistent"
        ) is None

    async def test_cascade_delete_project_removes_rules(self, db: Database) -> None:
        pid = await self._create_project(db, "cascade-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="cascade",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.projects.delete(pid)
        assert await db.repos.crawl_rules.get(rule.id) is None

    async def test_cascade_delete_project_removes_rule_versions(
        self, db: Database
    ) -> None:
        pid = await self._create_project(db, "deep-cascade-proj")
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=pid, name="deep-cascade",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule.id, version=1, rule_body="{}")
        )
        await db.repos.rule_test_results.create(
            RuleTestResultCreate(
                rule_id=rule.id, test_url="https://example.com", status="success"
            )
        )
        await db.repos.projects.delete(pid)
        # All cascaded
        versions = await db.repos.rule_versions.list_by_rule(rule.id)
        assert versions == []
        results = await db.repos.rule_test_results.list_by_rule(rule.id)
        assert results == []


# ------------------------------------------------------------------
# Repository: Jobs
# ------------------------------------------------------------------


class TestJobsRepository:
    async def test_create_and_get(self, db: Database) -> None:
        job = await db.repos.jobs.create(
            JobCreate(site="burghound", limit_n=5)
        )
        assert job.site == "burghound"
        assert job.status == "pending"
        assert job.limit_n == 5
        assert job.executor == "local"
        assert job.headless is True
        assert job.item_count == 0

    async def test_create_with_all_fields(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="job-full-proj", site="burghound")
        )
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=project.id, name="job-rule",
                page_type="search", rule_body="{}",
            )
        )
        job = await db.repos.jobs.create(
            JobCreate(
                site="burghound",
                project_id=project.id,
                rule_id=rule.id,
                executor="local",
                executor_meta='{"timeout": 30}',
                limit_n=25,
                headless=False,
                meta='{"note": "test"}',
            )
        )
        assert job.project_id == project.id
        assert job.rule_id == rule.id
        assert job.executor_meta == '{"timeout": 30}'
        assert job.headless is False
        assert job.meta == '{"note": "test"}'

    async def test_update_status_running(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.update_status(job.id, "running")
        fetched = await db.repos.jobs.get(job.id)
        assert fetched is not None
        assert fetched.status == "running"
        assert fetched.started_at is not None
        assert fetched.finished_at is None

    async def test_update_status_completed(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.update_status(job.id, "running")
        await db.repos.jobs.update_status(
            job.id, "completed", item_count=42, output_path="/data/out.json"
        )
        fetched = await db.repos.jobs.get(job.id)
        assert fetched is not None
        assert fetched.status == "completed"
        assert fetched.item_count == 42
        assert fetched.output_path == "/data/out.json"
        assert fetched.finished_at is not None
        assert fetched.duration_ms is not None
        assert fetched.duration_ms >= 0

    async def test_update_status_failed_with_error(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.update_status(job.id, "running")
        await db.repos.jobs.update_status(
            job.id, "failed", error="Connection timeout after 30s"
        )
        fetched = await db.repos.jobs.get(job.id)
        assert fetched is not None
        assert fetched.status == "failed"
        assert fetched.error == "Connection timeout after 30s"
        assert fetched.finished_at is not None

    async def test_update_status_cancelled(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.update_status(job.id, "running")
        await db.repos.jobs.update_status(job.id, "cancelled")
        fetched = await db.repos.jobs.get(job.id)
        assert fetched is not None
        assert fetched.status == "cancelled"
        assert fetched.finished_at is not None

    async def test_full_lifecycle_pending_to_completed(self, db: Database) -> None:
        """Full job lifecycle: pending -> running -> completed."""
        job = await db.repos.jobs.create(JobCreate(site="burghound", limit_n=10))
        assert job.status == "pending"
        assert job.started_at is None
        assert job.finished_at is None

        await db.repos.jobs.update_status(job.id, "running")
        running = await db.repos.jobs.get(job.id)
        assert running is not None
        assert running.status == "running"
        assert running.started_at is not None

        await db.repos.jobs.update_status(
            job.id, "completed", item_count=100, output_path="/data/result.json"
        )
        done = await db.repos.jobs.get(job.id)
        assert done is not None
        assert done.status == "completed"
        assert done.item_count == 100
        assert done.finished_at is not None
        assert done.duration_ms is not None
        assert done.duration_ms >= 0

    async def test_list_by_site(self, db: Database) -> None:
        await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.create(JobCreate(site="other"))
        results = await db.repos.jobs.list_by_site("burghound")
        assert len(results) == 2

    async def test_list_by_site_with_status_filter(self, db: Database) -> None:
        j1 = await db.repos.jobs.create(JobCreate(site="burghound"))
        j2 = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.jobs.update_status(j1.id, "running")

        running = await db.repos.jobs.list_by_site("burghound", status="running")
        assert len(running) == 1
        assert running[0].id == j1.id

        pending = await db.repos.jobs.list_by_site("burghound", status="pending")
        assert len(pending) == 1
        assert pending[0].id == j2.id

    async def test_list_recent(self, db: Database) -> None:
        for i in range(5):
            await db.repos.jobs.create(JobCreate(site=f"site{i}"))
        recent = await db.repos.jobs.list_recent(limit=3)
        assert len(recent) == 3

    async def test_update_nonexistent_job(self, db: Database) -> None:
        result = await db.repos.jobs.update_status("nonexistent-job", "running")
        assert result is False

    async def test_delete_job(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        deleted = await db.repos.jobs.delete(job.id)
        assert deleted is True
        assert await db.repos.jobs.get(job.id) is None


# ------------------------------------------------------------------
# Repository: Job Logs
# ------------------------------------------------------------------


class TestJobLogsRepository:
    async def test_create_and_list(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="INFO", message="Starting")
        )
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="DEBUG", message="Detail")
        )
        logs = await db.repos.job_logs.list_by_job(job.id)
        assert len(logs) == 2
        assert logs[0].message == "Starting"

    async def test_create_with_source(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        log = await db.repos.job_logs.create(
            JobLogCreate(
                job_id=job.id, level="INFO",
                message="From crawler", source="burghound.crawler",
            )
        )
        assert log.source == "burghound.crawler"

    async def test_create_fk_violation(self, db: Database) -> None:
        with pytest.raises(aiosqlite.IntegrityError):
            await db.repos.job_logs.create(
                JobLogCreate(
                    job_id="nonexistent-job", level="INFO", message="orphan"
                )
            )

    async def test_filter_by_level(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="INFO", message="a")
        )
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="ERROR", message="b")
        )
        errors = await db.repos.job_logs.list_by_job(job.id, level="ERROR")
        assert len(errors) == 1
        assert errors[0].level == "ERROR"

    async def test_cursor_pagination(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        for i in range(5):
            await db.repos.job_logs.create(
                JobLogCreate(job_id=job.id, level="INFO", message=f"msg{i}")
            )
        page1 = await db.repos.job_logs.list_by_job(job.id, limit=3)
        assert len(page1) == 3
        page2 = await db.repos.job_logs.list_by_job(
            job.id, after_id=page1[-1].id, limit=3
        )
        assert len(page2) == 2
        # IDs are monotonically increasing
        assert page2[0].id > page1[-1].id

    async def test_delete_by_job(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="INFO", message="x")
        )
        count = await db.repos.job_logs.delete_by_job(job.id)
        assert count == 1
        assert await db.repos.job_logs.list_by_job(job.id) == []

    async def test_cascade_delete_job_removes_logs(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        await db.repos.job_logs.create(
            JobLogCreate(job_id=job.id, level="INFO", message="will be deleted")
        )
        await db.repos.jobs.delete(job.id)
        logs = await db.repos.job_logs.list_by_job(job.id)
        assert logs == []

    async def test_list_by_job_empty(self, db: Database) -> None:
        job = await db.repos.jobs.create(JobCreate(site="burghound"))
        logs = await db.repos.job_logs.list_by_job(job.id)
        assert logs == []


# ------------------------------------------------------------------
# Repository: Credentials
# ------------------------------------------------------------------


class TestCredentialsRepository:
    async def test_upsert_and_get(self, db: Database) -> None:
        cred = await db.repos.credentials.upsert_credential(
            CredentialUpsert(
                site="burghound", email="a@b.com", password_enc="enc123"
            )
        )
        assert cred.site == "burghound"
        assert cred.email == "a@b.com"
        assert cred.updated_at  # non-empty

    async def test_upsert_overwrites(self, db: Database) -> None:
        await db.repos.credentials.upsert_credential(
            CredentialUpsert(
                site="burghound", email="old@b.com", password_enc="enc1"
            )
        )
        cred = await db.repos.credentials.upsert_credential(
            CredentialUpsert(
                site="burghound", email="new@b.com", password_enc="enc2"
            )
        )
        assert cred.email == "new@b.com"
        # Still only one row
        assert await db.repos.credentials.count() == 1

    async def test_upsert_with_notes(self, db: Database) -> None:
        cred = await db.repos.credentials.upsert_credential(
            CredentialUpsert(
                site="burghound", email="a@b.com",
                password_enc="enc", notes="test account",
            )
        )
        assert cred.notes == "test account"

    async def test_get_nonexistent(self, db: Database) -> None:
        assert await db.repos.credentials.get("no-site") is None

    async def test_delete(self, db: Database) -> None:
        await db.repos.credentials.upsert_credential(
            CredentialUpsert(site="to-del", email="x", password_enc="x")
        )
        deleted = await db.repos.credentials.delete("to-del")
        assert deleted is True
        assert await db.repos.credentials.get("to-del") is None

    async def test_list_sites(self, db: Database) -> None:
        await db.repos.credentials.upsert_credential(
            CredentialUpsert(site="b", email="x", password_enc="x")
        )
        await db.repos.credentials.upsert_credential(
            CredentialUpsert(site="a", email="x", password_enc="x")
        )
        sites = await db.repos.credentials.list_sites()
        assert sites == ["a", "b"]


# ------------------------------------------------------------------
# Repository: Schedules
# ------------------------------------------------------------------


class TestSchedulesRepository:
    async def test_create_and_get(self, db: Database) -> None:
        sched = await db.repos.schedules.create(
            ScheduleCreate(site="burghound", cron_expr="0 */6 * * *")
        )
        assert sched.cron_expr == "0 */6 * * *"
        assert sched.enabled is True
        assert sched.limit_n == 10

    async def test_create_with_project_and_rule(self, db: Database) -> None:
        project = await db.repos.projects.create(
            ProjectCreate(name="sched-proj", site="burghound")
        )
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=project.id, name="sched-rule",
                page_type="search", rule_body="{}",
            )
        )
        sched = await db.repos.schedules.create(
            ScheduleCreate(
                site="burghound", cron_expr="0 0 * * *",
                project_id=project.id, rule_id=rule.id, limit_n=50,
            )
        )
        assert sched.project_id == project.id
        assert sched.rule_id == rule.id
        assert sched.limit_n == 50

    async def test_list_enabled(self, db: Database) -> None:
        await db.repos.schedules.create(
            ScheduleCreate(site="a", cron_expr="* * * * *", enabled=True)
        )
        await db.repos.schedules.create(
            ScheduleCreate(site="b", cron_expr="* * * * *", enabled=False)
        )
        enabled = await db.repos.schedules.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].site == "a"

    async def test_mark_run(self, db: Database) -> None:
        sched = await db.repos.schedules.create(
            ScheduleCreate(site="a", cron_expr="* * * * *")
        )
        await db.repos.schedules.mark_run(
            sched.id, next_run="2026-02-09T00:00:00Z"
        )
        fetched = await db.repos.schedules.get(sched.id)
        assert fetched is not None
        assert fetched.last_run is not None
        assert fetched.next_run == "2026-02-09T00:00:00Z"

    async def test_update_schedule(self, db: Database) -> None:
        sched = await db.repos.schedules.create(
            ScheduleCreate(site="a", cron_expr="* * * * *")
        )
        await db.repos.schedules.update(
            sched.id,
            ScheduleUpdate(cron_expr="0 */12 * * *", limit_n=50).model_dump(
                exclude_none=True
            ),
        )
        fetched = await db.repos.schedules.get(sched.id)
        assert fetched is not None
        assert fetched.cron_expr == "0 */12 * * *"
        assert fetched.limit_n == 50

    async def test_delete_schedule(self, db: Database) -> None:
        sched = await db.repos.schedules.create(
            ScheduleCreate(site="a", cron_expr="* * * * *")
        )
        deleted = await db.repos.schedules.delete(sched.id)
        assert deleted is True
        assert await db.repos.schedules.get(sched.id) is None


# ------------------------------------------------------------------
# Repository: Request Kits
# ------------------------------------------------------------------


class TestRequestKitsRepository:
    async def test_create_and_get(self, db: Database) -> None:
        kit = await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound",
                format="curl",
                snippet_enc="enc_snippet",
                cookies_enc="enc_cookies",
            )
        )
        assert kit.site == "burghound"
        assert kit.format == "curl"
        assert kit.used_count == 0
        assert kit.last_used is None

    async def test_create_with_all_optional_fields(self, db: Database) -> None:
        kit = await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound",
                format="httpx",
                snippet_enc="snippet",
                cookies_enc="cookies",
                headers_enc="headers",
                csrf_extractor='{"source":"cookie","key":"_token"}',
                user_agent="Mozilla/5.0",
                expires_at="2026-02-10T00:00:00Z",
                notes="test kit",
            )
        )
        assert kit.headers_enc == "headers"
        assert kit.csrf_extractor is not None
        assert kit.user_agent == "Mozilla/5.0"
        assert kit.expires_at == "2026-02-10T00:00:00Z"
        assert kit.notes == "test kit"

    async def test_latest_for_site(self, db: Database) -> None:
        await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound", format="curl",
                snippet_enc="old", cookies_enc="old",
            )
        )
        await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound", format="httpx",
                snippet_enc="new", cookies_enc="new",
            )
        )
        latest = await db.repos.request_kits.latest_for_site("burghound")
        assert latest is not None
        assert latest.format == "httpx"

    async def test_latest_for_site_no_kits(self, db: Database) -> None:
        assert await db.repos.request_kits.latest_for_site("no-site") is None

    async def test_latest_for_site_isolates_sites(self, db: Database) -> None:
        await db.repos.request_kits.create(
            RequestKitCreate(
                site="site-a", format="curl",
                snippet_enc="a", cookies_enc="a",
            )
        )
        await db.repos.request_kits.create(
            RequestKitCreate(
                site="site-b", format="httpx",
                snippet_enc="b", cookies_enc="b",
            )
        )
        latest_a = await db.repos.request_kits.latest_for_site("site-a")
        assert latest_a is not None
        assert latest_a.site == "site-a"

    async def test_increment_used(self, db: Database) -> None:
        kit = await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound", format="curl",
                snippet_enc="s", cookies_enc="c",
            )
        )
        await db.repos.request_kits.increment_used(kit.id)
        await db.repos.request_kits.increment_used(kit.id)
        fetched = await db.repos.request_kits.get(kit.id)
        assert fetched is not None
        assert fetched.used_count == 2
        assert fetched.last_used is not None

    async def test_increment_used_nonexistent(self, db: Database) -> None:
        result = await db.repos.request_kits.increment_used("no-kit")
        assert result is False

    async def test_list_by_site(self, db: Database) -> None:
        for _ in range(3):
            await db.repos.request_kits.create(
                RequestKitCreate(
                    site="burghound", format="curl",
                    snippet_enc="s", cookies_enc="c",
                )
            )
        kits = await db.repos.request_kits.list_by_site("burghound", limit=2)
        assert len(kits) == 2

    async def test_list_by_site_empty(self, db: Database) -> None:
        kits = await db.repos.request_kits.list_by_site("no-site")
        assert kits == []

    async def test_delete_kit(self, db: Database) -> None:
        kit = await db.repos.request_kits.create(
            RequestKitCreate(
                site="burghound", format="curl",
                snippet_enc="s", cookies_enc="c",
            )
        )
        deleted = await db.repos.request_kits.delete(kit.id)
        assert deleted is True
        assert await db.repos.request_kits.get(kit.id) is None


# ------------------------------------------------------------------
# Repository: Site Capabilities
# ------------------------------------------------------------------


class TestSiteCapabilitiesRepository:
    async def test_upsert_and_get(self, db: Database) -> None:
        cap = await db.repos.site_capabilities.upsert_capability(
            SiteCapabilityUpsert(
                site="burghound",
                logout_strategy=json.dumps(
                    {"type": "ui_click", "selector": "a[href*=logout]"}
                ),
                login_validator=json.dumps(
                    {"type": "dom_text", "success_selector": ".user-menu"}
                ),
                token_validator=json.dumps(
                    {"type": "dom_text", "test_url": "/account"}
                ),
            )
        )
        assert cap.site == "burghound"
        assert cap.supports_request_kit is True
        assert cap.csrf_required is False
        assert cap.csrf_source is None

    async def test_upsert_with_csrf(self, db: Database) -> None:
        cap = await db.repos.site_capabilities.upsert_capability(
            SiteCapabilityUpsert(
                site="csrf-site",
                logout_strategy="{}",
                login_validator="{}",
                token_validator="{}",
                csrf_required=True,
                csrf_source="cookie",
                csrf_key="_token",
            )
        )
        assert cap.csrf_required is True
        assert cap.csrf_source == "cookie"
        assert cap.csrf_key == "_token"

    async def test_upsert_overwrites(self, db: Database) -> None:
        await db.repos.site_capabilities.upsert_capability(
            SiteCapabilityUpsert(
                site="overwrite-site",
                supports_request_kit=True,
                logout_strategy='{"type":"url_get"}',
                login_validator="{}",
                token_validator="{}",
            )
        )
        cap = await db.repos.site_capabilities.upsert_capability(
            SiteCapabilityUpsert(
                site="overwrite-site",
                supports_request_kit=False,
                logout_strategy='{"type":"ui_click"}',
                login_validator="{}",
                token_validator="{}",
            )
        )
        assert cap.supports_request_kit is False
        assert '"ui_click"' in cap.logout_strategy
        assert await db.repos.site_capabilities.count() == 1

    async def test_get_nonexistent(self, db: Database) -> None:
        assert await db.repos.site_capabilities.get("no-site") is None

    async def test_list_sites(self, db: Database) -> None:
        for site in ["z_site", "a_site"]:
            await db.repos.site_capabilities.upsert_capability(
                SiteCapabilityUpsert(
                    site=site,
                    logout_strategy="{}",
                    login_validator="{}",
                    token_validator="{}",
                )
            )
        sites = await db.repos.site_capabilities.list_sites()
        assert sites == ["a_site", "z_site"]

    async def test_delete_capability(self, db: Database) -> None:
        await db.repos.site_capabilities.upsert_capability(
            SiteCapabilityUpsert(
                site="to-del",
                logout_strategy="{}",
                login_validator="{}",
                token_validator="{}",
            )
        )
        deleted = await db.repos.site_capabilities.delete("to-del")
        assert deleted is True
        assert await db.repos.site_capabilities.get("to-del") is None


# ------------------------------------------------------------------
# Repository: Rule Versions
# ------------------------------------------------------------------


class TestRuleVersionsRepository:
    async def _setup(self, db: Database, suffix: str = "") -> str:
        p = await db.repos.projects.create(
            ProjectCreate(name=f"rv-project{suffix}", site="burghound")
        )
        r = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=p.id, name=f"rv-rule{suffix}",
                page_type="search", rule_body="{}",
            )
        )
        return r.id

    async def test_create_and_list(self, db: Database) -> None:
        rule_id = await self._setup(db, "-cl")
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule_id, version=1, rule_body='{"v":1}')
        )
        await db.repos.rule_versions.create(
            RuleVersionCreate(
                rule_id=rule_id, version=2,
                rule_body='{"v":2}', change_note="added field",
            )
        )
        versions = await db.repos.rule_versions.list_by_rule(rule_id)
        assert len(versions) == 2
        assert versions[0].version == 2  # DESC order
        assert versions[1].version == 1

    async def test_get_version(self, db: Database) -> None:
        rule_id = await self._setup(db, "-gv")
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule_id, version=1, rule_body='{"v":1}')
        )
        v = await db.repos.rule_versions.get_version(rule_id, 1)
        assert v is not None
        assert v.rule_body == '{"v":1}'

    async def test_get_version_nonexistent(self, db: Database) -> None:
        rule_id = await self._setup(db, "-gvn")
        v = await db.repos.rule_versions.get_version(rule_id, 999)
        assert v is None

    async def test_latest_version(self, db: Database) -> None:
        rule_id = await self._setup(db, "-lv")
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule_id, version=1, rule_body='{"v":1}')
        )
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule_id, version=2, rule_body='{"v":2}')
        )
        latest = await db.repos.rule_versions.latest_version(rule_id)
        assert latest is not None
        assert latest.version == 2

    async def test_latest_version_empty(self, db: Database) -> None:
        rule_id = await self._setup(db, "-lve")
        latest = await db.repos.rule_versions.latest_version(rule_id)
        assert latest is None

    async def test_unique_constraint_rule_id_version(self, db: Database) -> None:
        rule_id = await self._setup(db, "-uc")
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule_id, version=1, rule_body='{"v":1}')
        )
        with pytest.raises(aiosqlite.IntegrityError):
            await db.repos.rule_versions.create(
                RuleVersionCreate(
                    rule_id=rule_id, version=1, rule_body='{"v":1 dup}'
                )
            )

    async def test_cascade_delete_rule_removes_versions(
        self, db: Database
    ) -> None:
        p = await db.repos.projects.create(
            ProjectCreate(name="cascade-v-proj", site="burghound")
        )
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=p.id, name="cascade-v-rule",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.rule_versions.create(
            RuleVersionCreate(rule_id=rule.id, version=1, rule_body="{}")
        )
        await db.repos.crawl_rules.delete(rule.id)
        versions = await db.repos.rule_versions.list_by_rule(rule.id)
        assert versions == []


# ------------------------------------------------------------------
# Repository: Rule Test Results
# ------------------------------------------------------------------


class TestRuleTestResultsRepository:
    async def _setup(self, db: Database, suffix: str = "") -> str:
        p = await db.repos.projects.create(
            ProjectCreate(name=f"rtr-project{suffix}", site="burghound")
        )
        r = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=p.id, name=f"rtr-rule{suffix}",
                page_type="search", rule_body="{}",
            )
        )
        return r.id

    async def test_create_and_list(self, db: Database) -> None:
        rule_id = await self._setup(db, "-cl")
        await db.repos.rule_test_results.create(
            RuleTestResultCreate(
                rule_id=rule_id,
                test_url="https://example.com",
                status="success",
                extracted='[{"a":1}]',
                duration_ms=350,
            )
        )
        results = await db.repos.rule_test_results.list_by_rule(rule_id)
        assert len(results) == 1
        assert results[0].status == "success"
        assert results[0].duration_ms == 350

    async def test_create_failed_result(self, db: Database) -> None:
        rule_id = await self._setup(db, "-fail")
        result = await db.repos.rule_test_results.create(
            RuleTestResultCreate(
                rule_id=rule_id,
                test_url="https://example.com/broken",
                status="failed",
                errors='["selector not found: .nonexistent"]',
                duration_ms=120,
            )
        )
        assert result.status == "failed"
        assert result.errors is not None
        assert result.extracted is None

    async def test_list_returns_most_recent_first(self, db: Database) -> None:
        rule_id = await self._setup(db, "-order")
        for i in range(3):
            await db.repos.rule_test_results.create(
                RuleTestResultCreate(
                    rule_id=rule_id,
                    test_url=f"https://example.com/{i}",
                    status="success",
                )
            )
        results = await db.repos.rule_test_results.list_by_rule(rule_id)
        assert len(results) == 3
        # Most recent last URL should be first (DESC order)
        assert results[0].test_url == "https://example.com/2"

    async def test_list_respects_limit(self, db: Database) -> None:
        rule_id = await self._setup(db, "-lim")
        for i in range(5):
            await db.repos.rule_test_results.create(
                RuleTestResultCreate(
                    rule_id=rule_id,
                    test_url=f"https://example.com/{i}",
                    status="success",
                )
            )
        results = await db.repos.rule_test_results.list_by_rule(
            rule_id, limit=3
        )
        assert len(results) == 3

    async def test_cascade_delete(self, db: Database) -> None:
        p = await db.repos.projects.create(
            ProjectCreate(name="cascade-tr-proj", site="burghound")
        )
        rule = await db.repos.crawl_rules.create(
            CrawlRuleCreate(
                project_id=p.id, name="cascade-tr-rule",
                page_type="search", rule_body="{}",
            )
        )
        await db.repos.rule_test_results.create(
            RuleTestResultCreate(
                rule_id=rule.id, test_url="https://example.com",
                status="success",
            )
        )
        await db.repos.crawl_rules.delete(rule.id)
        results = await db.repos.rule_test_results.list_by_rule(rule.id)
        assert results == []


# ------------------------------------------------------------------
# Repository: KV Store
# ------------------------------------------------------------------


class TestKVStoreRepository:
    async def test_set_and_get(self, db: Database) -> None:
        await db.repos.kv_store.set_value("theme", "dark")
        val = await db.repos.kv_store.get_value("theme")
        assert val == "dark"

    async def test_get_nonexistent(self, db: Database) -> None:
        assert await db.repos.kv_store.get_value("no-key") is None

    async def test_overwrite(self, db: Database) -> None:
        await db.repos.kv_store.set_value("k", "v1")
        await db.repos.kv_store.set_value("k", "v2")
        assert await db.repos.kv_store.get_value("k") == "v2"

    async def test_delete_key(self, db: Database) -> None:
        await db.repos.kv_store.set_value("del", "x")
        deleted = await db.repos.kv_store.delete_key("del")
        assert deleted is True
        assert await db.repos.kv_store.get_value("del") is None

    async def test_delete_nonexistent_key(self, db: Database) -> None:
        result = await db.repos.kv_store.delete_key("never-existed")
        assert result is False

    async def test_get_many(self, db: Database) -> None:
        await db.repos.kv_store.set_value("prefix.a", "1")
        await db.repos.kv_store.set_value("prefix.b", "2")
        await db.repos.kv_store.set_value("other.c", "3")
        result = await db.repos.kv_store.get_many("prefix.")
        assert result == {"prefix.a": "1", "prefix.b": "2"}

    async def test_get_many_empty(self, db: Database) -> None:
        result = await db.repos.kv_store.get_many("nonexistent.")
        assert result == {}

    async def test_store_json_value(self, db: Database) -> None:
        data = {"key": "value", "nested": {"a": 1}}
        await db.repos.kv_store.set_value("json_data", json.dumps(data))
        raw = await db.repos.kv_store.get_value("json_data")
        assert raw is not None
        parsed = json.loads(raw)
        assert parsed == data


# ------------------------------------------------------------------
# Cross-cutting: BaseRepository generic methods
# ------------------------------------------------------------------


class TestBaseRepositoryGenericMethods:
    """Test generic BaseRepository methods via the projects repo."""

    async def test_find_by_multiple_filters(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="multi-f1", site="burghound", status="active")
        )
        await db.repos.projects.create(
            ProjectCreate(name="multi-f2", site="burghound", status="archived")
        )
        await db.repos.projects.create(
            ProjectCreate(name="multi-f3", site="other", status="active")
        )
        results = await db.repos.projects.find_by(
            site="burghound", status="active"
        )
        assert len(results) == 1
        assert results[0].name == "multi-f1"

    async def test_find_by_no_filters_returns_all(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="all-1", site="a")
        )
        await db.repos.projects.create(
            ProjectCreate(name="all-2", site="b")
        )
        results = await db.repos.projects.find_by()
        assert len(results) == 2

    async def test_find_by_with_ordering_and_limit(self, db: Database) -> None:
        for i in range(5):
            await db.repos.projects.create(
                ProjectCreate(name=f"ord-{i}", site="burghound")
            )
        results = await db.repos.projects.find_by(
            order_by="name ASC", limit=3, site="burghound"
        )
        assert len(results) == 3
        assert results[0].name == "ord-0"
        assert results[2].name == "ord-2"

    async def test_count_with_null_filter(self, db: Database) -> None:
        await db.repos.projects.create(
            ProjectCreate(name="null-test", site="burghound")
        )
        # description is NULL by default
        count = await db.repos.projects.count(description=None)
        assert count == 1

    async def test_update_nonexistent_returns_false(self, db: Database) -> None:
        result = await db.repos.projects.update(
            "nonexistent-pk", {"name": "nope"}
        )
        assert result is False
