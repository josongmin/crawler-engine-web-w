from __future__ import annotations

# pyright: reportUnusedFunction=false
# FastAPI route handlers are registered via decorators, so they appear unused to static analysis
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wine_crawler.admin.db.connection import Database
from wine_crawler.admin.db.enums import WorkflowStatus
from wine_crawler.admin.db.models import (
    ActionDef,
    CompileResult,
    CrawlRule,
    CrawlRuleCreate,
    CrawlRuleUpdate,
    Job,
    JobCreate,
    JobLog,
    LintResult,
    Project,
    ProjectCreate,
    ProjectUpdate,
    RequestKit,
    RequestKitCreate,
    RuleVersion,
    SiteCapability,
    SiteCapabilityUpsert,
    Workflow,
    WorkflowCreate,
    WorkflowNodeLog,
    WorkflowRun,
    WorkflowUpdate,
)
from wine_crawler.admin.services.catalog import get_action, get_catalog
from wine_crawler.admin.services.compiler import compile_workflow
from wine_crawler.admin.services.runner import WorkflowRunner, run_ws_hub
from wine_crawler.admin.services.validator import lint_workflow
from wine_crawler.config import Settings, ensure_dirs
from wine_crawler.sites.registry import list_sites


def _utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def create_app() -> FastAPI:
    settings = Settings()
    ensure_dirs(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = Database(settings.admin_db_path)
        await db.connect()
        app.state.settings = settings
        app.state.db = db
        try:
            yield
        finally:
            await db.disconnect()

    app = FastAPI(title="Wine Crawler Admin API", version="0.1.0", lifespan=lifespan)

    # CORS for frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files (served after API routes)
    admin_ui_dist = Path(__file__).parent.parent.parent.parent / "admin-ui" / "dist"
    if admin_ui_dist.exists():
        app.mount("/static", StaticFiles(directory=str(admin_ui_dist)), name="static")

        @app.get("/")
        async def serve_index():
            return FileResponse(admin_ui_dist / "index.html")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            # SPA fallback: serve index.html for non-API routes
            if not path.startswith("api") and not path.startswith("ws"):
                return FileResponse(admin_ui_dist / "index.html")
            raise HTTPException(status_code=404)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "ts": _utc_iso()}

    # ------------------------------------------------------------------
    # Sites
    # ------------------------------------------------------------------

    @app.get("/api/sites")
    async def sites() -> dict[str, Any]:
        sites_list = list_sites()
        # TODO: enrich with capabilities from DB
        return {"sites": sites_list}

    @app.get("/api/sites/{site}/capabilities")
    async def get_site_capabilities(site: str) -> SiteCapability:
        db: Database = app.state.db
        cap = await db.repos.site_capabilities.get(site)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"No capabilities for site: {site}")
        return cap

    @app.put("/api/sites/{site}/capabilities")
    async def update_site_capabilities(site: str, payload: SiteCapabilityUpsert) -> SiteCapability:
        db: Database = app.state.db
        if payload.site != site:
            raise HTTPException(status_code=400, detail="Site mismatch")
        return await db.repos.site_capabilities.upsert_capability(payload)

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    @app.get("/api/projects")
    async def list_projects(site: str | None = None) -> list[Project]:
        db: Database = app.state.db
        if site:
            return await db.repos.projects.list_by_site(site)
        return await db.repos.projects.list_all(order_by="created_at DESC")

    @app.post("/api/projects")
    async def create_project(payload: ProjectCreate) -> Project:
        db: Database = app.state.db
        # Check name uniqueness
        existing = await db.repos.projects.get_by_name(payload.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Project '{payload.name}' already exists")
        return await db.repos.projects.create(payload)

    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str) -> Project:
        db: Database = app.state.db
        project = await db.repos.projects.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return project

    @app.put("/api/projects/{project_id}")
    async def update_project(project_id: str, payload: ProjectUpdate) -> Project:
        db: Database = app.state.db
        success = await db.repos.projects.update_project(project_id, payload)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return await db.repos.projects.get(project_id)  # type: ignore[return-value]

    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str) -> dict[str, str]:
        db: Database = app.state.db
        success = await db.repos.projects.delete(project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return {"status": "deleted", "id": project_id}

    @app.get("/api/projects/{project_id}/stats")
    async def get_project_stats(project_id: str) -> dict[str, Any]:
        db: Database = app.state.db
        project = await db.repos.projects.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return await db.repos.projects.get_stats(project_id)

    # ------------------------------------------------------------------
    # Crawl Rules
    # ------------------------------------------------------------------

    @app.get("/api/rules")
    async def list_rules(
        project_id: str | None = None, active_only: bool = False
    ) -> list[CrawlRule]:
        db: Database = app.state.db
        if project_id:
            return await db.repos.crawl_rules.list_by_project(project_id, active_only=active_only)
        return await db.repos.crawl_rules.list_all(order_by="created_at DESC")

    @app.post("/api/rules")
    async def create_rule(payload: CrawlRuleCreate) -> CrawlRule:
        db: Database = app.state.db
        return await db.repos.crawl_rules.create(payload)

    @app.get("/api/rules/{rule_id}")
    async def get_rule(rule_id: str) -> CrawlRule:
        db: Database = app.state.db
        rule = await db.repos.crawl_rules.get(rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
        return rule

    @app.put("/api/rules/{rule_id}")
    async def update_rule(rule_id: str, payload: CrawlRuleUpdate) -> CrawlRule:
        db: Database = app.state.db
        success = await db.repos.crawl_rules.update_rule(rule_id, payload)
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
        return await db.repos.crawl_rules.get(rule_id)  # type: ignore[return-value]

    @app.delete("/api/rules/{rule_id}")
    async def delete_rule(rule_id: str) -> dict[str, str]:
        db: Database = app.state.db
        success = await db.repos.crawl_rules.delete(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
        return {"status": "deleted", "id": rule_id}

    @app.get("/api/rules/{rule_id}/versions")
    async def list_rule_versions(rule_id: str) -> list[RuleVersion]:
        db: Database = app.state.db
        return await db.repos.rule_versions.list_by_rule(rule_id)

    @app.get("/api/rules/{rule_id}/versions/{version}")
    async def get_rule_version(rule_id: str, version: int) -> RuleVersion:
        db: Database = app.state.db
        ver = await db.repos.rule_versions.get_version(rule_id, version)
        if ver is None:
            raise HTTPException(
                status_code=404, detail=f"Version {version} not found for rule {rule_id}"
            )
        return ver

    # ------------------------------------------------------------------
    # Request Kits
    # ------------------------------------------------------------------

    @app.get("/api/request-kits/{site}/latest")
    async def get_latest_kit(site: str) -> RequestKit | None:
        db: Database = app.state.db
        return await db.repos.request_kits.latest_for_site(site)

    @app.get("/api/request-kits/{site}/history")
    async def list_kit_history(site: str, limit: Annotated[int, Query(ge=1, le=500)] = 20) -> list[RequestKit]:
        db: Database = app.state.db
        return await db.repos.request_kits.list_by_site(site, limit=limit)

    @app.get("/api/request-kits/{site}/{kit_id}")
    async def get_kit(site: str, kit_id: str) -> RequestKit:
        db: Database = app.state.db
        kit = await db.repos.request_kits.get(kit_id)
        if kit is None or kit.site != site:
            raise HTTPException(status_code=404, detail=f"Kit not found: {kit_id}")
        return kit

    @app.post("/api/request-kits/{site}/export")
    async def export_kit(site: str, payload: RequestKitCreate) -> RequestKit:
        db: Database = app.state.db
        if payload.site != site:
            raise HTTPException(status_code=400, detail="Site mismatch")
        return await db.repos.request_kits.create(payload)

    @app.delete("/api/request-kits/{site}/{kit_id}")
    async def delete_kit(site: str, kit_id: str) -> dict[str, str]:
        db: Database = app.state.db
        kit = await db.repos.request_kits.get(kit_id)
        if kit is None or kit.site != site:
            raise HTTPException(status_code=404, detail=f"Kit not found: {kit_id}")
        success = await db.repos.request_kits.delete(kit_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete kit")
        return {"status": "deleted", "id": kit_id}

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    @app.get("/api/jobs")
    async def jobs(limit: Annotated[int, Query(ge=1, le=500)] = 20, site: str | None = None) -> list[Job]:
        db: Database = app.state.db
        if site:
            return await db.repos.jobs.list_by_site(site, limit=limit)
        return await db.repos.jobs.list_recent(limit=limit)

    @app.post("/api/jobs")
    async def create_job(payload: JobCreate) -> Job:
        db: Database = app.state.db

        # Create job record
        job = await db.repos.jobs.create(payload)

        # Submit to executor based on executor type
        if payload.executor == "aws_sqs":
            from wine_crawler.admin.services.execution.aws_sqs import AWSSQSExecutor

            queue_url = payload.executor_meta or os.environ.get("SQS_QUEUE_URL", "")
            if not queue_url:
                raise HTTPException(
                    status_code=400,
                    detail="SQS_QUEUE_URL required for aws_sqs executor (set executor_meta or env var)",
                )

            executor = AWSSQSExecutor(queue_url=queue_url)
            _ = await executor.submit(job)
        elif payload.executor == "local":
            from wine_crawler.admin.services.execution.local import LocalExecutor

            executor = LocalExecutor()
            _ = await executor.submit(job)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown executor: {payload.executor}")

        return job

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str) -> Job:
        db: Database = app.state.db
        job = await db.repos.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return job

    @app.get("/api/jobs/{job_id}/logs")
    async def job_logs(job_id: str, limit: Annotated[int, Query(ge=1, le=1000)] = 500, after_id: int | None = None) -> list[JobLog]:
        db: Database = app.state.db
        return await db.repos.job_logs.list_by_job(job_id, limit=limit, after_id=after_id)

    # ------------------------------------------------------------------
    # Action Catalog
    # ------------------------------------------------------------------

    @app.get("/api/catalog")
    async def list_catalog(site: str | None = None) -> list[ActionDef]:
        return get_catalog(site=site)

    @app.get("/api/catalog/{action_id:path}")
    async def get_catalog_action(action_id: str) -> ActionDef:
        action = get_action(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")
        return action

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------

    @app.get("/api/workflows")
    async def list_workflows(site: str | None = None) -> list[Workflow]:
        db: Database = app.state.db
        if site:
            return await db.repos.workflows.list_by_site(site)
        return await db.repos.workflows.list_recent()

    @app.post("/api/workflows")
    async def create_workflow(payload: WorkflowCreate) -> Workflow:
        db: Database = app.state.db
        return await db.repos.workflows.create(payload)

    @app.get("/api/workflows/{wf_id}")
    async def get_workflow(wf_id: str) -> Workflow:
        db: Database = app.state.db
        wf = await db.repos.workflows.get(wf_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {wf_id}")
        return wf

    @app.put("/api/workflows/{wf_id}")
    async def update_workflow(wf_id: str, payload: WorkflowUpdate) -> Workflow:
        db: Database = app.state.db
        success = await db.repos.workflows.update_workflow(wf_id, payload)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {wf_id}")
        return await db.repos.workflows.get(wf_id)  # type: ignore[return-value]

    @app.delete("/api/workflows/{wf_id}")
    async def delete_workflow(wf_id: str) -> dict[str, str]:
        db: Database = app.state.db
        success = await db.repos.workflows.delete(wf_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {wf_id}")
        return {"status": "deleted", "id": wf_id}

    # ------------------------------------------------------------------
    # Compile & Validate
    # ------------------------------------------------------------------

    @app.post("/api/workflows/{wf_id}/compile")
    async def compile_workflow_route(wf_id: str) -> CompileResult:
        db: Database = app.state.db
        wf = await db.repos.workflows.get(wf_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {wf_id}")

        result = compile_workflow(wf.graph_json, wf.site)

        # Persist compiled result and update status
        status = WorkflowStatus.VALID if result.valid else WorkflowStatus.INVALID
        _ = await db.repos.workflows.update_workflow(
            wf_id,
            WorkflowUpdate(
                compiled_json=json.dumps(result.model_dump()),
                status=status,
            ),
        )
        return result

    class _ValidatePayload(BaseModel):
        graph_json: str = Field(max_length=5_000_000)
        site: str = Field(min_length=1, max_length=50)

    @app.post("/api/workflows/validate")
    async def validate_workflow(payload: _ValidatePayload) -> LintResult:
        return lint_workflow(payload.graph_json, payload.site)

    # ------------------------------------------------------------------
    # Workflow Runs
    # ------------------------------------------------------------------

    @app.get("/api/workflows/{wf_id}/runs")
    async def list_workflow_runs(wf_id: str, limit: Annotated[int, Query(ge=1, le=500)] = 20) -> list[WorkflowRun]:
        db: Database = app.state.db
        return await db.repos.workflow_runs.list_by_workflow(wf_id, limit=limit)

    @app.post("/api/workflows/{wf_id}/run")
    async def run_workflow(wf_id: str) -> WorkflowRun:
        db: Database = app.state.db
        wf = await db.repos.workflows.get(wf_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {wf_id}")
        if not wf.compiled_json:
            raise HTTPException(
                status_code=400, detail="Workflow must be compiled before running"
            )

        compiled = CompileResult(**json.loads(wf.compiled_json))
        if not compiled.valid:
            raise HTTPException(
                status_code=400, detail="Cannot run an invalid workflow - fix errors first"
            )

        runner = WorkflowRunner(db)
        run_id = await runner.start_run(wf_id, compiled)
        run = await db.repos.workflow_runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=500, detail="Failed to create run")
        return run

    @app.get("/api/workflow-runs/{run_id}")
    async def get_workflow_run(run_id: str) -> WorkflowRun:
        db: Database = app.state.db
        run = await db.repos.workflow_runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return run

    @app.get("/api/workflow-runs/{run_id}/logs")
    async def get_workflow_run_logs(
        run_id: str, node_id: str | None = None, limit: Annotated[int, Query(ge=1, le=1000)] = 500
    ) -> list[WorkflowNodeLog]:
        db: Database = app.state.db
        return await db.repos.workflow_node_logs.list_by_run(
            run_id, node_id=node_id, limit=limit
        )

    # ------------------------------------------------------------------
    # WebSocket (MVP: connection + basic status)
    # ------------------------------------------------------------------

    @app.websocket("/ws/logs")
    async def ws_logs(ws: WebSocket) -> None:
        await ws.accept()
        await ws.send_json(
            {"type": "status", "timestamp": _utc_iso(), "data": {"message": "connected"}}
        )
        try:
            while True:
                # Keep the socket open; client may send pings/filters later.
                _ = await ws.receive_text()
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/jobs/{job_id}")
    async def ws_job(ws: WebSocket, job_id: str) -> None:
        await ws.accept()
        await ws.send_json(
            {
                "type": "status",
                "timestamp": _utc_iso(),
                "data": {"message": "connected", "job_id": job_id},
            }
        )
        try:
            while True:
                _ = await ws.receive_text()
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/workflow-runs/{run_id}")
    async def ws_workflow_run(ws: WebSocket, run_id: str) -> None:
        await ws.accept()
        run_ws_hub.subscribe(run_id, ws)
        await ws.send_json(
            {
                "type": "status",
                "timestamp": _utc_iso(),
                "data": {"message": "connected", "run_id": run_id},
            }
        )
        try:
            while True:
                _ = await ws.receive_text()
        except WebSocketDisconnect:
            run_ws_hub.unsubscribe(run_id, ws)

    return app
