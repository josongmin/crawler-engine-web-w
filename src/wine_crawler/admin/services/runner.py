"""Workflow Runner: executes a compiled DAG node-by-node.

The runner walks the ``execution_order`` from a ``CompileResult``,
executing each node sequentially. Node execution is currently
simulated (MVP); real action dispatch will be added per-site.

WebSocket broadcasts keep the UI updated in real-time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wine_crawler.admin.db.connection import Database

from wine_crawler.admin.db.enums import NodeStatus, RunStatus
from wine_crawler.admin.db.models import (
    CompileResult,
    WorkflowNodeLogCreate,
    WorkflowRunCreate,
)

logger = logging.getLogger(__name__)


# ── WebSocket Hub (per run_id) ──────────────────────────


class _RunWsHub:
    """Manages WebSocket connections for a single run."""

    def __init__(self) -> None:
        # No parent class, so no super() call needed
        self._subscribers: dict[str, list[Any]] = {}  # run_id → [ws, ...]

    def subscribe(self, run_id: str, ws: Any) -> None:
        self._subscribers.setdefault(run_id, []).append(ws)

    def unsubscribe(self, run_id: str, ws: Any) -> None:
        subs = self._subscribers.get(run_id, [])
        if ws in subs:
            subs.remove(ws)
        if not subs:
            _ = self._subscribers.pop(run_id, None)

    async def broadcast(self, run_id: str, message: dict[str, Any]) -> None:
        subs = self._subscribers.get(run_id, [])
        dead: list[Any] = []
        for ws in subs:
            try:
                await ws.send_json(message)
            except (ConnectionError, RuntimeError, OSError):
                dead.append(ws)
            except Exception:
                logger.debug("WS broadcast error for run %s", run_id, exc_info=True)
                dead.append(ws)
        for ws in dead:
            subs.remove(ws)


# Singleton hub — shared across the app
run_ws_hub = _RunWsHub()

# Active tasks tracking to prevent garbage collection (RUF006)
_active_tasks: set[asyncio.Task[None]] = set()


# ── Runner ──────────────────────────────────────────────


class WorkflowRunner:
    """Executes a compiled workflow DAG."""

    def __init__(self, db: Database) -> None:  # type: ignore[name-defined]
        self._db = db

    async def start_run(self, workflow_id: str, compiled: CompileResult) -> str:
        """Create a run record and launch execution in background."""
        run = await self._db.repos.workflow_runs.create(
            WorkflowRunCreate(workflow_id=workflow_id)
        )
        run_id = run.id

        # Launch in background - store task to prevent garbage collection (RUF006)
        task = asyncio.create_task(self._execute(run_id, compiled))
        _active_tasks.add(task)
        task.add_done_callback(_active_tasks.discard)
        return run_id

    async def _execute(self, run_id: str, compiled: CompileResult) -> None:
        """Main execution loop — walks nodes in topological order."""
        node_states: dict[str, str] = {
            node.node_id: NodeStatus.IDLE for node in compiled.nodes
        }

        try:
            _ = await self._db.repos.workflow_runs.update_status(run_id, RunStatus.RUNNING)
            await self._broadcast(
                run_id,
                "run_started",
                {"run_id": run_id, "node_count": len(compiled.nodes)},
            )

            await self._run_all_nodes(run_id, compiled, node_states)

            has_errors = any(v == NodeStatus.ERROR for v in node_states.values())
            final_status = RunStatus.FAILED if has_errors else RunStatus.COMPLETED
            _ = await self._db.repos.workflow_runs.update_status(run_id, final_status)
            await self._broadcast(
                run_id,
                "run_completed",
                {"run_id": run_id, "status": final_status, "node_states": node_states},
            )

        except asyncio.CancelledError:
            logger.info("Workflow run %s cancelled", run_id)
            _ = await self._db.repos.workflow_runs.update_status(
                run_id, RunStatus.CANCELLED, error="Cancelled"
            )
            raise
        except Exception as exc:
            logger.exception("Workflow run %s failed", run_id)
            _ = await self._db.repos.workflow_runs.update_status(
                run_id, RunStatus.FAILED, error=str(exc)
            )
            await self._broadcast(
                run_id,
                "run_error",
                {"run_id": run_id, "error": str(exc)},
            )

    async def _run_all_nodes(
        self,
        run_id: str,
        compiled: CompileResult,
        node_states: dict[str, str],
    ) -> None:
        """Walk nodes in topological order, executing each."""
        depends_on: dict[str, list[str]] = {
            node.node_id: node.depends_on for node in compiled.nodes
        }
        node_configs: dict[str, dict[str, Any]] = {
            node.node_id: {"action_id": node.action_id, "config": node.config}
            for node in compiled.nodes
        }

        for node_id in compiled.execution_order:
            if node_id not in node_states:
                continue

            deps = depends_on.get(node_id, [])
            dep_failed = any(
                node_states.get(dep) not in (NodeStatus.SUCCESS, None)
                for dep in deps
                if dep in node_states
            )

            if dep_failed:
                node_states[node_id] = NodeStatus.SKIPPED
                await self._log(run_id, node_id, "WARNING", "Skipped: dependency failed")
                await self._broadcast_node_status(run_id, node_id, NodeStatus.SKIPPED)
                continue

            await self._run_single_node(run_id, node_id, node_configs, node_states)

    async def _run_single_node(
        self,
        run_id: str,
        node_id: str,
        node_configs: dict[str, dict[str, Any]],
        node_states: dict[str, str],
    ) -> None:
        """Execute one node with error handling and state updates."""
        node_states[node_id] = NodeStatus.RUNNING
        await self._broadcast_node_status(run_id, node_id, NodeStatus.RUNNING)
        await self._save_node_states(run_id, node_states)

        node_cfg = node_configs.get(node_id)
        if not node_cfg:
            node_states[node_id] = NodeStatus.ERROR
            await self._log(run_id, node_id, "ERROR", f"No config for node '{node_id}'")
            await self._broadcast_node_status(run_id, node_id, NodeStatus.ERROR)
            await self._save_node_states(run_id, node_states)
            return

        action_id = node_cfg["action_id"]
        config = node_cfg["config"]

        try:
            await self._execute_node(run_id, node_id, action_id, config)
            node_states[node_id] = NodeStatus.SUCCESS
            await self._log(run_id, node_id, "INFO", f"Completed: {action_id}")
            await self._broadcast_node_status(run_id, node_id, NodeStatus.SUCCESS)
        except (KeyError, ValueError, RuntimeError) as exc:
            node_states[node_id] = NodeStatus.ERROR
            await self._log(run_id, node_id, "ERROR", f"Failed: {exc}")
            await self._broadcast_node_status(run_id, node_id, NodeStatus.ERROR)
        except Exception as exc:
            logger.warning("Unexpected error on node %s: %s", node_id, exc, exc_info=True)
            node_states[node_id] = NodeStatus.ERROR
            await self._log(run_id, node_id, "ERROR", f"Unexpected error: {exc}")
            await self._broadcast_node_status(run_id, node_id, NodeStatus.ERROR)

        await self._save_node_states(run_id, node_states)

    async def _execute_node(
        self,
        run_id: str,
        node_id: str,
        action_id: str,
        config: dict[str, Any],
    ) -> None:
        """Execute a single node. MVP: simulated execution with delay."""
        _ = config  # Unused in MVP - will be used for real action dispatch (ARG002)
        await self._log(run_id, node_id, "INFO", f"Executing: {action_id}")

        # Simulated execution delay (0.5-2s)
        delay = 0.5 + random.random() * 1.5
        await asyncio.sleep(delay)

        # In the future, dispatch to real action handlers based on action_id:
        #   match action_id:
        #       case "*.login": await login_handler(...)
        #       case "*.search": await search_handler(...)
        #       ...

    async def _log(
        self, run_id: str, node_id: str, level: str, message: str
    ) -> None:
        """Write a log entry to DB and broadcast."""
        _ = await self._db.repos.workflow_node_logs.create(
            WorkflowNodeLogCreate(
                run_id=run_id,
                node_id=node_id,
                level=level,
                message=message,
            )
        )
        await self._broadcast(
            run_id,
            "node_log",
            {"node_id": node_id, "level": level, "message": message},
        )

    async def _save_node_states(
        self, run_id: str, states: dict[str, str]
    ) -> None:
        """Persist node states as JSON."""
        _ = await self._db.repos.workflow_runs.update_node_states(
            run_id, json.dumps(states)
        )

    async def _broadcast_node_status(
        self, run_id: str, node_id: str, status: str
    ) -> None:
        await self._broadcast(
            run_id,
            "node_status",
            {"node_id": node_id, "status": status},
        )

    async def _broadcast(
        self, run_id: str, msg_type: str, data: dict[str, Any]
    ) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        await run_ws_hub.broadcast(
            run_id,
            {"type": msg_type, "timestamp": now, "data": data},
        )
