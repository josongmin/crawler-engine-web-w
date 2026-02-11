"""Shared enums for the admin workflow engine.

These values are mirrored 1:1 in the frontend at
``admin-ui/src/shared/config/enums.ts``.  Keep both files in sync.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum for Python 3.10 compatibility (StrEnum is 3.11+)."""

    def __str__(self) -> str:
        return self.value

# ── Action / Node Classification ────────────────────────


class ActionCategory(StrEnum):
    AUTH = "auth"
    CRAWL = "crawl"
    EXPORT = "export"
    CONTROL = "control"
    DATA = "data"


# ── Resource Types (action requires / provides) ────────


class ResourceType(StrEnum):
    CREDENTIAL = "credential"
    BROWSER_CONTEXT = "browser_context"
    SESSION_ACTIVE = "session_active"
    REQUEST_KIT = "request_kit"
    STORAGE_STATE = "storage_state"
    CRAWL_RULE = "crawl_rule"
    DATASET = "dataset"
    PERSONA = "persona"


# ── Node Execution Status ──────────────────────────────


class NodeStatus(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


# ── Workflow-Level Status ──────────────────────────────


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    VALID = "valid"
    INVALID = "invalid"


# ── Workflow Run Status ────────────────────────────────


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Lint Severity ──────────────────────────────────────


class LintSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ── Edge Handle Kind ──────────────────────────────────


class EdgeKind(StrEnum):
    NORMAL = "output"
    ERROR = "error"
