/* ── Workflow Node Type Registry ──────────────────────
 *
 * Every atomic operation that can appear in a workflow
 * is defined here. The registry drives:
 *   - NodePalette (drag-and-drop source)
 *   - WorkflowNode (visual rendering)
 *   - NodeConfigPanel (configuration fields)
 *
 * Categories: auth · crawl · export · control · data
 * ──────────────────────────────────────────────────── */

import {
  LogIn,
  LogOut,
  ClipboardPaste,
  RefreshCw,
  ShieldCheck,
  Search,
  FileText,
  MessageSquare,
  List,
  Terminal,
  Send,
  FileJson,
  Timer,
  GitBranch,
  Save,
  Bell,
  type LucideIcon,
} from "lucide-react";

// ── Core types ─────────────────────────────────────────

export type NodeCategory = "auth" | "crawl" | "export" | "control" | "data";

export interface ConfigField {
  key: string;
  label: string;
  type: "text" | "number" | "boolean" | "select";
  options?: { value: string; label: string }[];
  default: unknown;
  placeholder?: string;
}

export interface NodeTypeDef {
  /** Unique type key, e.g. "login", "search" */
  type: string;
  category: NodeCategory;
  name: string;
  description: string;
  icon: LucideIcon;
  /** Tailwind color classes for icon bg + text */
  colorClass: string;
  /** Whether the node accepts an incoming edge */
  hasInput: boolean;
  /** Whether the node emits data / triggers the next node */
  hasOutput: boolean;
  /** If true, the node has a second "error" output handle */
  hasErrorOutput?: boolean;
  /** Configurable fields shown in NodeConfigPanel */
  configFields: ConfigField[];
}

// ── Category metadata ──────────────────────────────────

export const CATEGORIES: {
  id: NodeCategory;
  label: string;
  color: string;
}[] = [
  { id: "auth", label: "Authentication", color: "text-status-success" },
  { id: "crawl", label: "Crawl", color: "text-status-info" },
  { id: "export", label: "Export", color: "text-status-warning" },
  { id: "control", label: "Control", color: "text-fg-muted" },
  { id: "data", label: "Data", color: "text-violet-500 dark:text-violet-400" },
];

// ── Node definitions ───────────────────────────────────

export const NODE_DEFS: NodeTypeDef[] = [
  // ── Auth ───────────────────────────────────────────
  {
    type: "login",
    category: "auth",
    name: "Login",
    description: "Playwright browser login using stored credentials",
    icon: LogIn,
    colorClass: "bg-status-success-muted text-status-success",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      { key: "headless", label: "Headless", type: "boolean", default: true },
      {
        key: "timeout",
        label: "Timeout (s)",
        type: "number",
        default: 30,
      },
    ],
  },
  {
    type: "logout",
    category: "auth",
    name: "Logout",
    description: "Capability-based logout (URL/POST/UI click)",
    icon: LogOut,
    colorClass: "bg-status-success-muted text-status-success",
    hasInput: true,
    hasOutput: true,
    configFields: [],
  },
  {
    type: "paste-auth",
    category: "auth",
    name: "Paste Auth",
    description: "Inject cookies/headers from clipboard or template",
    icon: ClipboardPaste,
    colorClass: "bg-status-success-muted text-status-success",
    hasInput: true,
    hasOutput: true,
    configFields: [
      {
        key: "mode",
        label: "Mode",
        type: "select",
        options: [
          { value: "cookies", label: "Cookie String" },
          { value: "headers", label: "Headers" },
          { value: "storage-state", label: "Storage State JSON" },
        ],
        default: "cookies",
      },
      {
        key: "template",
        label: "Template / Content",
        type: "text",
        default: "",
        placeholder: "PHPSESSID=...; tn_user=...",
      },
    ],
  },
  {
    type: "refresh-session",
    category: "auth",
    name: "Refresh Session",
    description: "Refresh session state and TTL",
    icon: RefreshCw,
    colorClass: "bg-status-success-muted text-status-success",
    hasInput: true,
    hasOutput: true,
    configFields: [],
  },
  {
    type: "check-session",
    category: "auth",
    name: "Check Session",
    description: "Branch: session active → yes/no",
    icon: ShieldCheck,
    colorClass: "bg-status-success-muted text-status-success",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true, // "no" branch
    configFields: [],
  },

  // ── Crawl ──────────────────────────────────────────
  {
    type: "search",
    category: "crawl",
    name: "Search",
    description: "Run search/list extraction with pagination",
    icon: Search,
    colorClass: "bg-status-info-muted text-status-info",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      { key: "limit", label: "Limit", type: "number", default: 50 },
      {
        key: "ruleId",
        label: "Rule",
        type: "select",
        options: [
          { value: "r1", label: "search-results v3" },
          { value: "r2", label: "wine-detail v2" },
          { value: "r3", label: "producer-list v1" },
        ],
        default: "r1",
      },
      { key: "headless", label: "Headless", type: "boolean", default: true },
      {
        key: "followLinks",
        label: "Follow Links",
        type: "boolean",
        default: false,
      },
    ],
  },
  {
    type: "detail",
    category: "crawl",
    name: "Detail Extract",
    description: "Extract individual item details from URLs",
    icon: FileText,
    colorClass: "bg-status-info-muted text-status-info",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      {
        key: "ruleId",
        label: "Rule",
        type: "select",
        options: [
          { value: "r2", label: "wine-detail v2" },
          { value: "r1", label: "search-results v3" },
        ],
        default: "r2",
      },
      { key: "headless", label: "Headless", type: "boolean", default: true },
      {
        key: "concurrency",
        label: "Concurrency",
        type: "number",
        default: 1,
      },
    ],
  },
  {
    type: "review",
    category: "crawl",
    name: "Review Extract",
    description: "Extract user reviews and ratings",
    icon: MessageSquare,
    colorClass: "bg-status-info-muted text-status-info",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      { key: "limit", label: "Limit", type: "number", default: 50 },
      {
        key: "ruleId",
        label: "Rule",
        type: "text",
        default: "",
        placeholder: "rule ID",
      },
    ],
  },
  {
    type: "list",
    category: "crawl",
    name: "List Extract",
    description: "Extract items from a list/table page",
    icon: List,
    colorClass: "bg-status-info-muted text-status-info",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      { key: "limit", label: "Limit", type: "number", default: 20 },
      {
        key: "ruleId",
        label: "Rule",
        type: "text",
        default: "",
        placeholder: "rule ID",
      },
    ],
  },

  // ── Export ─────────────────────────────────────────
  {
    type: "export-curl",
    category: "export",
    name: "Export cURL",
    description: "Export authenticated cURL snippet to clipboard/file",
    icon: Terminal,
    colorClass: "bg-status-warning-muted text-status-warning",
    hasInput: true,
    hasOutput: true,
    configFields: [
      {
        key: "baseUrl",
        label: "Base URL",
        type: "text",
        default: "",
        placeholder: "https://...",
      },
      {
        key: "minimalHeaders",
        label: "Minimal Headers",
        type: "boolean",
        default: true,
      },
    ],
  },
  {
    type: "export-httpx",
    category: "export",
    name: "Export httpx",
    description: "Export authenticated httpx Python snippet",
    icon: Send,
    colorClass: "bg-status-warning-muted text-status-warning",
    hasInput: true,
    hasOutput: true,
    configFields: [
      {
        key: "baseUrl",
        label: "Base URL",
        type: "text",
        default: "",
        placeholder: "https://...",
      },
    ],
  },
  {
    type: "export-storage",
    category: "export",
    name: "Export Storage State",
    description: "Export Playwright storage state JSON",
    icon: FileJson,
    colorClass: "bg-status-warning-muted text-status-warning",
    hasInput: true,
    hasOutput: true,
    configFields: [],
  },

  // ── Control ────────────────────────────────────────
  {
    type: "delay",
    category: "control",
    name: "Delay",
    description: "Wait before continuing to next node",
    icon: Timer,
    colorClass: "bg-status-neutral-muted text-status-neutral",
    hasInput: true,
    hasOutput: true,
    configFields: [
      { key: "seconds", label: "Seconds", type: "number", default: 5 },
      {
        key: "jitter",
        label: "Jitter (±s)",
        type: "number",
        default: 2,
      },
    ],
  },
  {
    type: "condition",
    category: "control",
    name: "Condition",
    description: "Branch based on a condition (yes → output, no → error)",
    icon: GitBranch,
    colorClass: "bg-status-neutral-muted text-status-neutral",
    hasInput: true,
    hasOutput: true,
    hasErrorOutput: true,
    configFields: [
      {
        key: "conditionType",
        label: "Condition",
        type: "select",
        options: [
          { value: "session-active", label: "Session is active" },
          { value: "items-gt", label: "Items count >" },
          { value: "status-ok", label: "Previous status = success" },
        ],
        default: "session-active",
      },
      {
        key: "value",
        label: "Value",
        type: "number",
        default: 0,
      },
    ],
  },

  // ── Data ───────────────────────────────────────────
  {
    type: "save-file",
    category: "data",
    name: "Save to File",
    description: "Save extracted data to JSON/CSV/JSONL",
    icon: Save,
    colorClass: "bg-violet-500/15 text-violet-500 dark:text-violet-400",
    hasInput: true,
    hasOutput: true,
    configFields: [
      {
        key: "format",
        label: "Format",
        type: "select",
        options: [
          { value: "json", label: "JSON" },
          { value: "csv", label: "CSV" },
          { value: "jsonl", label: "JSON Lines" },
        ],
        default: "json",
      },
      {
        key: "filename",
        label: "Filename",
        type: "text",
        default: "",
        placeholder: "auto-generated if empty",
      },
    ],
  },
  {
    type: "notify",
    category: "data",
    name: "Notify",
    description: "Send a notification (webhook or log entry)",
    icon: Bell,
    colorClass: "bg-violet-500/15 text-violet-500 dark:text-violet-400",
    hasInput: true,
    hasOutput: false,
    configFields: [
      {
        key: "message",
        label: "Message",
        type: "text",
        default: "Workflow completed",
        placeholder: "Notification message",
      },
    ],
  },
];

// ── Helpers ────────────────────────────────────────────

export function getNodeDef(type: string): NodeTypeDef | undefined {
  return NODE_DEFS.find((d) => d.type === type);
}

export function getNodesByCategory(
  category: NodeCategory,
): NodeTypeDef[] {
  return NODE_DEFS.filter((d) => d.category === category);
}

export function getDefaultConfig(type: string): Record<string, unknown> {
  const def = getNodeDef(type);
  if (!def) return {};
  return Object.fromEntries(
    def.configFields.map((f) => [f.key, f.default]),
  );
}
