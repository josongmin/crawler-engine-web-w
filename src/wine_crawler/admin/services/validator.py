"""Workflow Lint: lightweight static validation without auto-insertion.

The validator performs the same structural checks as the compiler but
does **not** auto-insert prerequisite nodes. This makes it fast enough
for real-time UI feedback (debounced on every graph edit).

Checks:
  - JSON parse validity
  - Empty graph
  - Missing nodeType
  - Dangling edges
  - Cycle detection (Kahn's algorithm)
  - Unreachable nodes (BFS from roots)
  - Site scope violations
  - Missing required resources
  - Missing crawl rule configuration
  - Unknown action IDs
"""

from __future__ import annotations

from wine_crawler.admin.db.enums import LintSeverity, ResourceType
from wine_crawler.admin.db.models import LintDiagnostic, LintResult
from wine_crawler.admin.services._graph_analysis import (
    GraphEdge,
    GraphNode,
    build_normal_incoming,
    build_normal_outgoing,
    detect_cycles,
    find_unreachable,
    parse_graph,
    validate_site_scope,
)
from wine_crawler.admin.services.catalog import get_action

# ── Resource Analysis (lint-only, no auto-insertion) ────


def _analyze_resources(
    topo_order: list[str],
    nodes: dict[str, GraphNode],
    normal_incoming: dict[str, list[str]],
) -> tuple[dict[str, set[ResourceType]], list[LintDiagnostic]]:
    """Analyze resource requirements and availability.

    Returns: (available_at, diagnostics)
    """
    diagnostics: list[LintDiagnostic] = []
    available_at: dict[str, set[ResourceType]] = {}

    runtime_provided: set[ResourceType] = {
        ResourceType.BROWSER_CONTEXT,
        ResourceType.CREDENTIAL,
        ResourceType.PERSONA,
    }

    for nid in topo_order:
        node = nodes.get(nid)
        if node is None:
            continue

        action = get_action(node.action_id)
        if not action:
            diagnostics.append(
                LintDiagnostic(
                    node_id=nid,
                    severity=LintSeverity.ERROR,
                    code="UNKNOWN_ACTION",
                    message=f"Action '{node.action_id}' not found in catalog",
                )
            )
            available_at[nid] = set()
            continue

        # Gather predecessor resources
        pred_resources: set[ResourceType] = set()
        for pred_id in normal_incoming.get(nid, []):
            if pred_id in available_at:
                pred_resources |= available_at[pred_id]

        # Check missing resources
        missing = set(action.requires) - pred_resources - runtime_provided

        for res in missing:
            if res == ResourceType.SESSION_ACTIVE:
                diagnostics.append(
                    LintDiagnostic(
                        node_id=nid,
                        severity=LintSeverity.INFO,
                        code="NEEDS_SESSION",
                        message=(
                            f"Node '{nid}' requires an active session - "
                            "compiler will auto-insert check-session + login"
                        ),
                    )
                )
            elif res == ResourceType.CRAWL_RULE:
                if not node.config.get("ruleId"):
                    diagnostics.append(
                        LintDiagnostic(
                            node_id=nid,
                            severity=LintSeverity.WARNING,
                            code="MISSING_RULE",
                            message=f"Node '{nid}' requires a crawl rule but 'ruleId' is not configured",
                        )
                    )
            elif res == ResourceType.DATASET:
                diagnostics.append(
                    LintDiagnostic(
                        node_id=nid,
                        severity=LintSeverity.WARNING,
                        code="MISSING_DATASET",
                        message=f"Node '{nid}' requires dataset input from a preceding crawl node",
                    )
                )
            elif res == ResourceType.STORAGE_STATE:
                diagnostics.append(
                    LintDiagnostic(
                        node_id=nid,
                        severity=LintSeverity.WARNING,
                        code="MISSING_STORAGE_STATE",
                        message=f"Node '{nid}' requires storage state from a login node",
                    )
                )
            else:
                diagnostics.append(
                    LintDiagnostic(
                        node_id=nid,
                        severity=LintSeverity.ERROR,
                        code="MISSING_RESOURCE",
                        message=f"Node '{nid}' requires '{res}' but no predecessor provides it",
                    )
                )

        # Accumulate provides
        available_at[nid] = pred_resources | set(action.provides)

    return available_at, diagnostics


# ── Burghound Logout Check ──────────────────────────────


def _check_burghound_logouts(
    site: str,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    available_at: dict[str, set[ResourceType]],
) -> list[LintDiagnostic]:
    """Check for Burghound terminal nodes needing auto-logout."""
    if site != "burghound":
        return []

    normal_outgoing = build_normal_outgoing(edges)

    return [
        LintDiagnostic(
            node_id=nid,
            severity=LintSeverity.INFO,
            code="BURGHOUND_AUTO_LOGOUT",
            message=(
                f"Terminal node '{nid}' holds an active session - "
                "compiler will auto-insert Burghound auto-logout"
            ),
        )
        for nid, node in nodes.items()
        if not normal_outgoing.get(nid)
        and nid in available_at
        and ResourceType.SESSION_ACTIVE in available_at.get(nid, set())
        and node.node_type not in ("logout", "auto-logout")
    ]


# ── Public API ──────────────────────────────────────────


def lint_workflow(graph_json: str, site: str) -> LintResult:
    """Stateless lint of a workflow graph. Returns diagnostics only, no mutations.

    Designed for real-time UI feedback - call on every graph change with debounce.
    """
    all_diagnostics: list[LintDiagnostic] = []

    # 1. Parse
    parsed = parse_graph(graph_json, site)
    all_diagnostics.extend(parsed.diagnostics)
    if not parsed.nodes:
        return LintResult(valid=False, diagnostics=all_diagnostics)

    # 2. Cycle detection
    topo_order, cycle_diags = detect_cycles(parsed.nodes, parsed.edges)
    all_diagnostics.extend(cycle_diags)
    if cycle_diags:
        has_errors = any(d.severity == LintSeverity.ERROR for d in all_diagnostics)
        return LintResult(valid=not has_errors, diagnostics=all_diagnostics)

    # 3. Unreachable nodes
    all_diagnostics.extend(find_unreachable(parsed.nodes, parsed.edges))

    # 4. Site scope
    all_diagnostics.extend(validate_site_scope(parsed.nodes, site))

    # 5. Resource analysis
    normal_incoming = build_normal_incoming(parsed.edges)
    available_at, resource_diags = _analyze_resources(
        topo_order, parsed.nodes, normal_incoming
    )
    all_diagnostics.extend(resource_diags)

    # 6. Burghound session warning
    all_diagnostics.extend(
        _check_burghound_logouts(site, parsed.nodes, parsed.edges, available_at)
    )

    has_errors = any(d.severity == LintSeverity.ERROR for d in all_diagnostics)
    return LintResult(valid=not has_errors, diagnostics=all_diagnostics)
