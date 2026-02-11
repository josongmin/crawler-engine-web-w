"""Action Catalog: declarative registry of all workflow actions.

Each action defines its resource contract (requires/provides) which
drives the DAG compiler's auto-insertion logic and the frontend
node palette.
"""

from __future__ import annotations

from wine_crawler.admin.db.enums import ActionCategory, ResourceType
from wine_crawler.admin.db.models import ActionConfigField, ActionDef

# ── Internal registry ────────────────────────────────

_CATALOG: list[ActionDef] = []


def _reg(action: ActionDef) -> ActionDef:
    _CATALOG.append(action)
    return action


# ── Public API ───────────────────────────────────────


def get_catalog(*, site: str | None = None) -> list[ActionDef]:
    """Return all actions, optionally filtered to a site (includes site-agnostic ``*``)."""
    if site is None:
        return list(_CATALOG)
    return [a for a in _CATALOG if a.site in (site, "*")]


def get_action(action_id: str) -> ActionDef | None:
    """Lookup a single action by its action_id."""
    return next((a for a in _CATALOG if a.action_id == action_id), None)


def get_actions_by_category(category: str) -> list[ActionDef]:
    """Return all actions in a category."""
    return [a for a in _CATALOG if a.category == category]


# ── Auth Actions ─────────────────────────────────────

_ = _reg(ActionDef(
    action_id="*.check-session",
    site="*",
    category=ActionCategory.AUTH,
    name="Check Session",
    description="Branch: session active \u2192 yes/no",
    requires=[ResourceType.BROWSER_CONTEXT],
    provides=[],
    inputs_schema=[],
    outputs_schema=["is_active"],
    branches=["yes", "no"],
    has_error_output=True,
))

_ = _reg(ActionDef(
    action_id="*.login",
    site="*",
    category=ActionCategory.AUTH,
    name="Login",
    description="Playwright browser login using stored credentials",
    requires=[ResourceType.CREDENTIAL, ResourceType.BROWSER_CONTEXT, ResourceType.PERSONA],
    provides=[ResourceType.SESSION_ACTIVE, ResourceType.STORAGE_STATE],
    inputs_schema=[
        ActionConfigField(key="headless", label="Headless", type="boolean", default=True),
        ActionConfigField(key="timeout", label="Timeout (s)", type="number", default=30),
    ],
    outputs_schema=["session_id", "storage_state_path"],
    has_error_output=True,
    failure_modes=["invalid_credentials", "account_locked", "captcha", "timeout"],
))

_ = _reg(ActionDef(
    action_id="*.logout",
    site="*",
    category=ActionCategory.AUTH,
    name="Logout",
    description="Capability-based logout (URL/POST/UI click)",
    requires=[ResourceType.BROWSER_CONTEXT],
    provides=[],
    inputs_schema=[],
    outputs_schema=[],
))

_ = _reg(ActionDef(
    action_id="*.paste-auth",
    site="*",
    category=ActionCategory.AUTH,
    name="Paste Auth",
    description="Inject cookies/headers from clipboard or template",
    requires=[ResourceType.BROWSER_CONTEXT],
    provides=[ResourceType.SESSION_ACTIVE],
    inputs_schema=[
        ActionConfigField(
            key="mode", label="Mode", type="select",
            options=[
                {"value": "cookies", "label": "Cookie String"},
                {"value": "headers", "label": "Headers"},
                {"value": "storage-state", "label": "Storage State JSON"},
            ],
            default="cookies",
        ),
        ActionConfigField(
            key="template", label="Template / Content", type="text",
            default="", placeholder="PHPSESSID=...; tn_user=...",
        ),
    ],
    outputs_schema=["injected_count"],
))

_ = _reg(ActionDef(
    action_id="*.refresh-session",
    site="*",
    category=ActionCategory.AUTH,
    name="Refresh Session",
    description="Refresh session state and TTL",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT],
    provides=[ResourceType.SESSION_ACTIVE],
    inputs_schema=[],
    outputs_schema=["ttl_remaining"],
))

# ── Crawl Actions ────────────────────────────────────

_ = _reg(ActionDef(
    action_id="*.search",
    site="*",
    category=ActionCategory.CRAWL,
    name="Search",
    description="Run search/list extraction with pagination",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT, ResourceType.CRAWL_RULE],
    provides=[ResourceType.DATASET],
    inputs_schema=[
        ActionConfigField(key="limit", label="Limit", type="number", default=50),
        ActionConfigField(
            key="ruleId", label="Rule", type="rule_select",
            default="", placeholder="rule ID",
        ),
        ActionConfigField(key="headless", label="Headless", type="boolean", default=True),
        ActionConfigField(key="followLinks", label="Follow Links", type="boolean", default=False),
    ],
    outputs_schema=["items", "item_count", "pages_crawled"],
    has_error_output=True,
    failure_modes=["session_expired", "rate_limited", "rule_error", "timeout"],
))

_ = _reg(ActionDef(
    action_id="*.detail",
    site="*",
    category=ActionCategory.CRAWL,
    name="Detail Extract",
    description="Extract individual item details from URLs",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT, ResourceType.CRAWL_RULE],
    provides=[ResourceType.DATASET],
    inputs_schema=[
        ActionConfigField(
            key="ruleId", label="Rule", type="rule_select",
            default="", placeholder="rule ID",
        ),
        ActionConfigField(key="headless", label="Headless", type="boolean", default=True),
        ActionConfigField(key="concurrency", label="Concurrency", type="number", default=1),
    ],
    outputs_schema=["items", "item_count"],
    has_error_output=True,
    failure_modes=["session_expired", "rule_error", "404_not_found", "timeout"],
))

_ = _reg(ActionDef(
    action_id="*.review",
    site="*",
    category=ActionCategory.CRAWL,
    name="Review Extract",
    description="Extract user reviews and ratings",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT],
    provides=[ResourceType.DATASET],
    inputs_schema=[
        ActionConfigField(key="limit", label="Limit", type="number", default=50),
        ActionConfigField(
            key="ruleId", label="Rule", type="text",
            default="", placeholder="rule ID",
        ),
    ],
    outputs_schema=["items", "item_count"],
    has_error_output=True,
    failure_modes=["session_expired", "timeout"],
))

_ = _reg(ActionDef(
    action_id="*.list",
    site="*",
    category=ActionCategory.CRAWL,
    name="List Extract",
    description="Extract items from a list/table page",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT],
    provides=[ResourceType.DATASET],
    inputs_schema=[
        ActionConfigField(key="limit", label="Limit", type="number", default=20),
        ActionConfigField(
            key="ruleId", label="Rule", type="text",
            default="", placeholder="rule ID",
        ),
    ],
    outputs_schema=["items", "item_count"],
    has_error_output=True,
    failure_modes=["session_expired", "timeout"],
))

# ── Export Actions ───────────────────────────────────

_ = _reg(ActionDef(
    action_id="*.export-curl",
    site="*",
    category=ActionCategory.EXPORT,
    name="Export cURL",
    description="Export authenticated cURL snippet to clipboard/file",
    requires=[ResourceType.SESSION_ACTIVE],
    provides=[ResourceType.REQUEST_KIT],
    inputs_schema=[
        ActionConfigField(
            key="baseUrl", label="Base URL", type="text",
            default="", placeholder="https://...",
        ),
        ActionConfigField(key="minimalHeaders", label="Minimal Headers", type="boolean", default=True),
    ],
    outputs_schema=["snippet", "kit_id"],
))

_ = _reg(ActionDef(
    action_id="*.export-httpx",
    site="*",
    category=ActionCategory.EXPORT,
    name="Export httpx",
    description="Export authenticated httpx Python snippet",
    requires=[ResourceType.SESSION_ACTIVE],
    provides=[ResourceType.REQUEST_KIT],
    inputs_schema=[
        ActionConfigField(
            key="baseUrl", label="Base URL", type="text",
            default="", placeholder="https://...",
        ),
    ],
    outputs_schema=["snippet", "kit_id"],
))

_ = _reg(ActionDef(
    action_id="*.export-storage",
    site="*",
    category=ActionCategory.EXPORT,
    name="Export Storage State",
    description="Export Playwright storage state JSON",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.STORAGE_STATE],
    provides=[ResourceType.REQUEST_KIT],
    inputs_schema=[],
    outputs_schema=["path"],
))

# ── Control Actions ──────────────────────────────────

_ = _reg(ActionDef(
    action_id="*.delay",
    site="*",
    category=ActionCategory.CONTROL,
    name="Delay",
    description="Wait before continuing to next node",
    requires=[],
    provides=[],
    inputs_schema=[
        ActionConfigField(key="seconds", label="Seconds", type="number", default=5),
        ActionConfigField(key="jitter", label="Jitter (\u00b1s)", type="number", default=2),
    ],
    outputs_schema=[],
))

_ = _reg(ActionDef(
    action_id="*.condition",
    site="*",
    category=ActionCategory.CONTROL,
    name="Condition",
    description="Branch based on a condition (yes \u2192 output, no \u2192 error)",
    requires=[],
    provides=[],
    inputs_schema=[
        ActionConfigField(
            key="conditionType", label="Condition", type="select",
            options=[
                {"value": "session-active", "label": "Session is active"},
                {"value": "items-gt", "label": "Items count >"},
                {"value": "status-ok", "label": "Previous status = success"},
            ],
            default="session-active",
        ),
        ActionConfigField(key="value", label="Value", type="number", default=0),
    ],
    outputs_schema=["result"],
    branches=["yes", "no"],
    has_error_output=True,
))

# ── Data Actions ─────────────────────────────────────

_ = _reg(ActionDef(
    action_id="*.save-file",
    site="*",
    category=ActionCategory.DATA,
    name="Save to File",
    description="Save extracted data to JSON/CSV/JSONL",
    requires=[ResourceType.DATASET],
    provides=[],
    inputs_schema=[
        ActionConfigField(
            key="format", label="Format", type="select",
            options=[
                {"value": "json", "label": "JSON"},
                {"value": "csv", "label": "CSV"},
                {"value": "jsonl", "label": "JSON Lines"},
            ],
            default="json",
        ),
        ActionConfigField(
            key="filename", label="Filename", type="text",
            default="", placeholder="auto-generated if empty",
        ),
    ],
    outputs_schema=["path", "size_bytes"],
))

_ = _reg(ActionDef(
    action_id="*.notify",
    site="*",
    category=ActionCategory.DATA,
    name="Notify",
    description="Send a notification (webhook or log entry)",
    requires=[],
    provides=[],
    inputs_schema=[
        ActionConfigField(
            key="message", label="Message", type="text",
            default="Workflow completed", placeholder="Notification message",
        ),
    ],
    outputs_schema=[],
))

# ── Burghound-Specific ──────────────────────────────

_ = _reg(ActionDef(
    action_id="burghound.auto-logout",
    site="burghound",
    category=ActionCategory.AUTH,
    name="Auto-Logout (Burghound)",
    description="Forced logout for Burghound single-session constraint (1h lockout prevention)",
    requires=[ResourceType.SESSION_ACTIVE, ResourceType.BROWSER_CONTEXT],
    provides=[],
    inputs_schema=[],
    outputs_schema=[],
))
