/* ── Shared Enums ─────────────────────────────────────
 *
 * Mirrored 1:1 from the Python backend at
 *   src/wine_crawler/admin/db/enums.py
 *
 * Uses "const object + type extraction" pattern for
 * both runtime values (iteration) and compile-time safety.
 * ──────────────────────────────────────────────────── */

// ── Action / Node Classification ────────────────────

export const ActionCategory = {
  AUTH: "auth",
  CRAWL: "crawl",
  EXPORT: "export",
  CONTROL: "control",
  DATA: "data",
} as const;
export type ActionCategory = (typeof ActionCategory)[keyof typeof ActionCategory];

// ── Resource Types (action requires / provides) ─────

export const ResourceType = {
  CREDENTIAL: "credential",
  BROWSER_CONTEXT: "browser_context",
  SESSION_ACTIVE: "session_active",
  REQUEST_KIT: "request_kit",
  STORAGE_STATE: "storage_state",
  CRAWL_RULE: "crawl_rule",
  DATASET: "dataset",
  PERSONA: "persona",
} as const;
export type ResourceType = (typeof ResourceType)[keyof typeof ResourceType];

// ── Node Execution Status ───────────────────────────

export const NodeStatus = {
  IDLE: "idle",
  QUEUED: "queued",
  RUNNING: "running",
  SUCCESS: "success",
  ERROR: "error",
  SKIPPED: "skipped",
} as const;
export type NodeStatus = (typeof NodeStatus)[keyof typeof NodeStatus];

// ── Workflow-Level Status ───────────────────────────

export const WorkflowStatus = {
  DRAFT: "draft",
  VALID: "valid",
  INVALID: "invalid",
} as const;
export type WorkflowStatus = (typeof WorkflowStatus)[keyof typeof WorkflowStatus];

// ── Workflow Run Status ─────────────────────────────

export const RunStatus = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;
export type RunStatus = (typeof RunStatus)[keyof typeof RunStatus];

// ── Lint Severity ───────────────────────────────────

export const LintSeverity = {
  ERROR: "error",
  WARNING: "warning",
  INFO: "info",
} as const;
export type LintSeverity = (typeof LintSeverity)[keyof typeof LintSeverity];

// ── Edge Handle Kind ────────────────────────────────

export const EdgeKind = {
  NORMAL: "output",
  ERROR: "error",
} as const;
export type EdgeKind = (typeof EdgeKind)[keyof typeof EdgeKind];
