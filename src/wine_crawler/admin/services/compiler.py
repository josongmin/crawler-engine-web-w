"""DAG Compiler: transforms a ReactFlow graph into an executable plan.

Pipeline:
  1. parse_graph()       - ReactFlow JSON -> internal GraphNode/GraphEdge
  2. detect_cycles()     - Kahn's algorithm (in-degree topological sort)
  3. find_unreachable()  - BFS from root nodes -> unreachable detection
  4. validate_site_scope() - reject cross-site action mixing
  5. resolve_resources() - auto-insert prerequisite nodes (login, check-session, auto-logout)
  6. topological_sort()  - final execution order

The compiler is the *write-path* counterpart of the validator (lint).
It performs all lint checks **plus** auto-insertion of missing nodes.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any
from uuid import uuid4

from wine_crawler.admin.db.enums import EdgeKind, LintSeverity, ResourceType
from wine_crawler.admin.db.models import CompiledNode, CompileResult, LintDiagnostic
from wine_crawler.admin.services._graph_analysis import (
    GraphEdge,
    GraphNode,
    build_normal_incoming,
    build_normal_outgoing,
    detect_cycles,
    find_unreachable,
    parse_graph,
    resolve_action_id,
    validate_site_scope,
)
from wine_crawler.admin.services.catalog import get_action

# pyright: reportUnknownVariableType=false
# GraphNode.config and GraphNode.position are properly typed in _graph_analysis

# ── Resource Resolution + Auto-Insertion ────────────────


def _make_auto_node_id() -> str:
    return f"auto-{uuid4().hex[:8]}"


def _insert_session_chain(
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    nid: str,
    node: GraphNode,
    site: str,
    predecessor_resources: set[ResourceType],
) -> tuple[list[str], list[GraphEdge], set[ResourceType]]:
    """Insert check-session + login chain before a node requiring SESSION_ACTIVE.

    Returns: (auto_inserted_ids, edges_to_add, updated_resources)
    """
    check_id = _make_auto_node_id()
    login_id = _make_auto_node_id()

    check_action_id = resolve_action_id("check-session", site)
    login_action_id = resolve_action_id("login", site)

    # Position auto-inserted nodes above the current node
    # GraphNode.position is dict[str, float]
    pos_x = node.position.get("x", 250)
    pos_y = node.position.get("y", 100)

    nodes[check_id] = GraphNode(
        id=check_id,
        node_type="check-session",
        action_id=check_action_id,
        config={},
        position={"x": pos_x, "y": pos_y - 300},
        auto_inserted=True,
    )
    nodes[login_id] = GraphNode(
        id=login_id,
        node_type="login",
        action_id=login_action_id,
        config={"headless": True, "timeout": 30},
        position={"x": pos_x, "y": pos_y - 150},
        auto_inserted=True,
    )

    # Rewire: predecessors -> check-session -> (yes) -> current node
    #                                        -> (no)  -> login -> current node
    new_edges_to_add = [
        GraphEdge(
            id=f"auto-e-{edge.source}-{check_id}",
            source=edge.source,
            target=check_id,
            kind=EdgeKind.NORMAL,
        )
        for edge in edges
        if edge.target == nid and edge.kind == EdgeKind.NORMAL
    ]

    new_edges_to_add.append(
        GraphEdge(
            id=f"auto-e-{check_id}-{nid}",
            source=check_id,
            target=nid,
            kind=EdgeKind.NORMAL,
        )
    )
    new_edges_to_add.append(
        GraphEdge(
            id=f"auto-e-{check_id}-{login_id}",
            source=check_id,
            target=login_id,
            kind=EdgeKind.ERROR,
        )
    )
    new_edges_to_add.append(
        GraphEdge(
            id=f"auto-e-{login_id}-{nid}",
            source=login_id,
            target=nid,
            kind=EdgeKind.NORMAL,
        )
    )

    login_action = get_action(login_action_id)
    provided: list[ResourceType] = login_action.provides if login_action else []
    updated_resources = predecessor_resources | set(provided)

    return [check_id, login_id], new_edges_to_add, updated_resources


def _report_missing_resource(
    nid: str,
    res: ResourceType,
    node_config: dict[str, Any],
    diagnostics: list[LintDiagnostic],
) -> None:
    """Report a missing resource as a diagnostic."""
    if res in (ResourceType.BROWSER_CONTEXT, ResourceType.CREDENTIAL, ResourceType.PERSONA):
        return
    if res == ResourceType.CRAWL_RULE:
        if not node_config.get("ruleId"):
            diagnostics.append(
                LintDiagnostic(
                    node_id=nid,
                    severity=LintSeverity.WARNING,
                    code="MISSING_RULE",
                    message=f"Node '{nid}' requires a crawl rule but 'ruleId' is not configured",
                )
            )
        return
    if res == ResourceType.DATASET:
        diagnostics.append(
            LintDiagnostic(
                node_id=nid,
                severity=LintSeverity.WARNING,
                code="MISSING_DATASET",
                message=f"Node '{nid}' requires dataset input from a preceding crawl node",
            )
        )
        return
    diagnostics.append(
        LintDiagnostic(
            node_id=nid,
            severity=LintSeverity.ERROR,
            code="MISSING_RESOURCE",
            message=f"Node '{nid}' requires '{res}' but it is not provided by any predecessor",
        )
    )


def _insert_burghound_logouts(
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    available_at: dict[str, set[ResourceType]],
) -> list[str]:
    """Auto-insert logout at terminal Burghound nodes with SESSION_ACTIVE."""
    auto_inserted: list[str] = []
    outgoing_map_final = build_normal_outgoing(edges)

    terminal_nodes = [
        nid
        for nid in nodes
        if not outgoing_map_final.get(nid)
        and nid in available_at
        and ResourceType.SESSION_ACTIVE in available_at.get(nid, set())
        and nodes[nid].node_type != "auto-logout"
    ]

    for terminal_id in terminal_nodes:
        logout_id = _make_auto_node_id()
        terminal_node = nodes[terminal_id]
        pos_x = terminal_node.position.get("x", 250)
        pos_y = terminal_node.position.get("y", 500)

        nodes[logout_id] = GraphNode(
            id=logout_id,
            node_type="auto-logout",
            action_id="burghound.auto-logout",
            config={},
            position={"x": pos_x, "y": pos_y + 150},
            auto_inserted=True,
        )
        edges.append(
            GraphEdge(
                id=f"auto-e-{terminal_id}-{logout_id}",
                source=terminal_id,
                target=logout_id,
                kind=EdgeKind.NORMAL,
            )
        )
        auto_inserted.append(logout_id)

    return auto_inserted


def _resolve_resources(
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    topo_order: list[str],
    site: str,
) -> tuple[dict[str, GraphNode], list[GraphEdge], list[str], list[LintDiagnostic]]:
    """Walk the DAG in topological order, tracking available resources.

    Auto-inserts prerequisite nodes when resources are missing:
    - SESSION_ACTIVE missing -> insert check-session + login chain
    - Burghound terminal nodes with SESSION_ACTIVE -> insert auto-logout

    Returns: (updated_nodes, updated_edges, auto_inserted_ids, diagnostics)
    """
    diagnostics: list[LintDiagnostic] = []
    auto_inserted: list[str] = []

    incoming_map = build_normal_incoming(edges)
    available_at: dict[str, set[ResourceType]] = {}

    for nid in topo_order:
        if nid not in nodes:
            continue

        node = nodes[nid]
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

        predecessor_resources: set[ResourceType] = set()
        for pred_id in incoming_map.get(nid, []):
            if pred_id in available_at:
                predecessor_resources |= available_at[pred_id]

        missing = set(action.requires) - predecessor_resources

        if ResourceType.SESSION_ACTIVE in missing:
            session_ids, new_edges, updated_resources = _insert_session_chain(
                nodes, edges, nid, node, site, predecessor_resources
            )

            edges_to_remove = {
                e.id for e in edges if e.target == nid and e.kind == EdgeKind.NORMAL
            }
            edges = [e for e in edges if e.id not in edges_to_remove]
            edges.extend(new_edges)

            check_id, login_id = session_ids
            check_action = get_action(resolve_action_id("check-session", site))
            login_action = get_action(resolve_action_id("login", site))

            check_provides: list[ResourceType] = check_action.provides if check_action else []
            login_provides: list[ResourceType] = login_action.provides if login_action else []
            available_at[check_id] = predecessor_resources | set(check_provides)
            available_at[login_id] = predecessor_resources | set(login_provides)

            auto_inserted.extend(session_ids)
            missing.discard(ResourceType.SESSION_ACTIVE)
            missing.discard(ResourceType.STORAGE_STATE)
            predecessor_resources = updated_resources

        for res in missing:
            _report_missing_resource(nid, res, node.config, diagnostics)

        available_at[nid] = predecessor_resources | set(action.provides)

    if site == "burghound":
        logout_ids = _insert_burghound_logouts(nodes, edges, available_at)
        auto_inserted.extend(logout_ids)

    return nodes, edges, auto_inserted, diagnostics


# ── Final Topological Sort ──────────────────────────────


def _final_topological_sort(
    nodes: dict[str, GraphNode], edges: list[GraphEdge]
) -> list[str]:
    """Topological sort on the (possibly augmented) graph."""
    in_degree: dict[str, int] = dict.fromkeys(nodes, 0)
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        adjacency[edge.source].append(edge.target)
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adjacency[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


# ── Build Compiled Nodes ────────────────────────────────


def _build_compiled_nodes(
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    execution_order: list[str],
) -> list[CompiledNode]:
    """Transform internal graph into CompiledNode list."""
    incoming = build_normal_incoming(edges)

    compiled: list[CompiledNode] = []
    for nid in execution_order:
        if nid not in nodes:
            continue
        node = nodes[nid]
        compiled.append(
            CompiledNode(
                node_id=nid,
                action_id=node.action_id,
                config=node.config,
                depends_on=incoming.get(nid, []),
                auto_inserted=node.auto_inserted,
            )
        )

    return compiled


# ── Public API ──────────────────────────────────────────


def compile_workflow(graph_json: str, site: str) -> CompileResult:
    """Compile a ReactFlow workflow graph into an executable plan."""
    all_diagnostics: list[LintDiagnostic] = []

    # 1. Parse
    parsed = parse_graph(graph_json, site)
    nodes = parsed.nodes
    edges = parsed.edges
    all_diagnostics.extend(parsed.diagnostics)
    if not nodes:
        return CompileResult(
            valid=False,
            execution_order=[],
            nodes=[],
            diagnostics=all_diagnostics,
            auto_inserted_nodes=[],
        )

    # 2. Cycle detection
    topo_order, cycle_diags = detect_cycles(nodes, edges)
    all_diagnostics.extend(cycle_diags)
    if cycle_diags:
        return CompileResult(
            valid=False,
            execution_order=[],
            nodes=[],
            diagnostics=all_diagnostics,
            auto_inserted_nodes=[],
        )

    # 3. Unreachable nodes
    all_diagnostics.extend(find_unreachable(nodes, edges))

    # 4. Site scope
    scope_diags = validate_site_scope(nodes, site)
    all_diagnostics.extend(scope_diags)
    if any(d.severity == LintSeverity.ERROR for d in scope_diags):
        return CompileResult(
            valid=False,
            execution_order=[],
            nodes=[],
            diagnostics=all_diagnostics,
            auto_inserted_nodes=[],
        )

    # 5. Resource resolution + auto-insertion
    nodes, edges, auto_inserted, resource_diags = _resolve_resources(
        nodes, edges, topo_order, site
    )
    all_diagnostics.extend(resource_diags)

    # 6. Final topological sort (on augmented graph)
    execution_order = _final_topological_sort(nodes, edges)

    # 7. Build compiled nodes
    compiled_nodes = _build_compiled_nodes(nodes, edges, execution_order)

    has_errors = any(d.severity == LintSeverity.ERROR for d in all_diagnostics)

    return CompileResult(
        valid=not has_errors,
        execution_order=execution_order,
        nodes=compiled_nodes,
        diagnostics=all_diagnostics,
        auto_inserted_nodes=auto_inserted,
    )
