/* ── Domain Types ───────────────────────────────── */

export interface Session {
  site: string;
  status: "active" | "inactive" | "expired" | "logged_out";
  created_at: string;
  last_login_at: string;
  last_logout_at: string;
  use_count: number;
  ttl_hours: number;
  user_agent: string;
  is_cleanly_closed: boolean;
}

export interface Persona {
  user_agent: string;
  viewport_width: number;
  viewport_height: number;
  screen_width: number;
  screen_height: number;
  locale: string;
  timezone_id: string;
  platform: string;
}

export interface Cookie {
  name: string;
  value: string;
  domain: string;
  path: string;
  expires: number;
  httpOnly: boolean;
  secure: boolean;
}

export interface RequestKit {
  id: string;
  site: string;
  format: "curl" | "httpx" | "cookies" | "storage_state";
  snippet: string;
  cookies: Cookie[];
  headers: Record<string, string>;
  expires_at: string;
  created_at: string;
  used_count: number;
}

export interface CrawlRule {
  id: string;
  project_id: string;
  name: string;
  page_type: "search" | "detail" | "list" | "pagination";
  url_pattern: string;
  version: number;
  rule_body: RuleBody;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleBody {
  name: string;
  page_type: string;
  url_pattern: string;
  pre_actions?: PreAction[];
  extract: ExtractConfig;
  pagination?: PaginationConfig;
  follow?: FollowConfig;
  throttle?: ThrottleConfig;
}

export interface PreAction {
  type: "wait" | "dismiss" | "click";
  selector: string;
  timeout_ms?: number;
}

export interface ExtractConfig {
  container: string | null;
  fields: Record<string, FieldDef>;
}

export interface FieldDef {
  selector: string | string[];
  type: "text" | "attr" | "html";
  attr?: string;
  optional?: boolean;
  transform?: TransformDef;
  post_process?: string;
}

export interface TransformDef {
  name: "trim" | "regex" | "absolute_url" | "int" | "float";
  pattern?: string;
  group?: number | "all";
  base?: string;
}

export interface PaginationConfig {
  type: "click" | "url_param";
  next_selector?: string;
  next_url_selector?: string;
  has_next?: string;
  max_pages: number;
  delay_between_ms: { min: number; max: number };
}

export interface FollowConfig {
  field: string;
  rule: string;
  merge_into_parent: boolean;
  dedupe_by?: string;
  cache_ttl_hours?: number;
}

export interface ThrottleConfig {
  requests_per_minute: number;
  delay_ms: { min: number; max: number };
}

export interface Job {
  id: string;
  project_id?: string;
  site: string;
  rule_id?: string;
  executor: "local" | "remote_proxy";
  status: "pending" | "running" | "success" | "failed" | "cancelled";
  limit_n: number;
  headless: boolean;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  item_count: number;
  error?: string;
}

export interface JobLog {
  id: number;
  job_id: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  message: string;
  timestamp: string;
  source: string;
}

export interface Project {
  id: string;
  name: string;
  site: string;
  description: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface SiteCapability {
  site: string;
  supports_request_kit: boolean;
  csrf_required: boolean;
}

export interface RuleTestResult {
  id: string;
  rule_id: string;
  test_url: string;
  status: "pass" | "fail" | "partial";
  extracted: Record<string, unknown>[];
  errors: string[];
  duration_ms: number;
}
