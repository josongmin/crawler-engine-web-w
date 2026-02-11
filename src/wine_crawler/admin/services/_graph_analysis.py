"""Shared graph analysis utilities for the compiler and validator.

Extracted to avoid ~200 lines of duplication between ``compiler.py``
and ``validator.py``.  Both modules import from here.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from wine_crawler.admin.db.enums import EdgeKind, LintSeverity
from wine_crawler.admin.db.models import LintDiagnostic
from wine_crawler.admin.services.catalog import get_action

# ── Parsed Graph Representation ──────────────────────────


@dataclass
class GraphNode:
    """Parsed representation of a ReactFlow node."""

    id: str
    node_type: str  # e.g. "login", "search"
    action_id: str  # e.g. "*.login", "burghound.auto-logout"
    config: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    position: dict[str, float] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    auto_inserted: bool = False


@dataclass
class GraphEdge:
    """Parsed representation of a ReactFlow edge."""

    id: str
    source: str
    target: str
    kind: EdgeKind = EdgeKind.NORMAL


@dataclass
class ParsedGraph:
    """Result of parsing a ReactFlow JSON graph."""

    nodes: dict[str, GraphNode]
    edges: list[GraphEdge]
    diagnostics: list[LintDiagnostic]


# ── Action ID Resolution ─────────────────────────────────


def resolve_action_id(node_type: str, site: str) -> str:
    """Map a frontend nodeType (e.g. ``"login"``) to a catalog action_id.

    Priority: site-specific (``burghound.login``) > generic (``*.login``).
    """
    site_specific = f"{site}.{node_type}"
    if get_action(site_specific):
        return site_specific
    return f"*.{node_type}"


# ── Graph Parsing ────────────────────────────────────────


def parse_graph(graph_json: str, site: str) -> ParsedGraph:
    """Parse ReactFlow JSON into internal representation."""
    diagnostics: list[LintDiagnostic] = []

    try:
        data = json.loads(graph_json)
    except json.JSONDecodeError as exc:
        diagnostics.append(
            LintDiagnostic(
                severity=LintSeverity.ERROR,
                code="PARSE_ERROR",
                message=f"Invalid JSON: {exc}",
            )
        )
        return ParsedGraph(nodes={}, edges=[], diagnostics=diagnostics)

    raw_nodes: list[dict[str, Any]] = data.get("nodes", [])
    raw_edges: list[dict[str, Any]] = data.get("edges", [])

    if not raw_nodes:
        diagnostics.append(
            LintDiagnostic(
                severity=LintSeverity.ERROR,
                code="EMPTY_GRAPH",
                message="Workflow has no nodes",
            )
        )
        return ParsedGraph(nodes={}, edges=[], diagnostics=diagnostics)

    nodes: dict[str, GraphNode] = {}
    for rn in raw_nodes:
        node_id = rn.get("id", "")
        node_data: dict[str, Any] = rn.get("data", {})
        node_type = node_data.get("nodeType", "")

        if not node_type:
            diagnostics.append(
                LintDiagnostic(
                    node_id=node_id,
                    severity=LintSeverity.ERROR,
                    code="MISSING_NODE_TYPE",
                    message=f"Node '{node_id}' has no nodeType",
                )
            )
            continue

        action_id = resolve_action_id(node_type, site)
        nodes[node_id] = GraphNode(
            id=node_id,
            node_type=node_type,
            action_id=action_id,
            config=node_data.get("config", {}),
            position=rn.get("position", {}),
            auto_inserted=node_data.get("autoInserted", False),
        )

    edges: list[GraphEdge] = []
    node_ids = set(nodes.keys())
    for re_item in raw_edges:
        src = re_item.get("source", "")
        tgt = re_item.get("target", "")

        if src not in node_ids:
            diagnostics.append(
                LintDiagnostic(
                    severity=LintSeverity.WARNING,
                    code="DANGLING_EDGE",
                    message=f"Edge source '{src}' not found",
                )
            )
            continue
        if tgt not in node_ids:
            diagnostics.append(
                LintDiagnostic(
                    severity=LintSeverity.WARNING,
                    code="DANGLING_EDGE",
                    message=f"Edge target '{tgt}' not found",
                )
            )
            continue

        handle = re_item.get("sourceHandle", "output")
        kind = EdgeKind.ERROR if handle == "error" else EdgeKind.NORMAL
        edges.append(GraphEdge(id=re_item.get("id", ""), source=src, target=tgt, kind=kind))

    return ParsedGraph(nodes=nodes, edges=edges, diagnostics=diagnostics)


# ── Cycle Detection (Kahn's Algorithm) ───────────────────


def detect_cycles(
    nodes: dict[str, GraphNode], edges: list[GraphEdge]
) -> tuple[list[str], list[LintDiagnostic]]:
    """Topological sort via Kahn's. Returns (order, diagnostics).

    If the graph has cycles, ``order`` will be shorter than ``len(nodes)``
    and a diagnostic will list the cycle-participating node IDs.
    """
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

    diagnostics: list[LintDiagnostic] = []
    if len(order) != len(nodes):
        cycle_nodes = [nid for nid in nodes if nid not in set(order)]
        diagnostics.append(
            LintDiagnostic(
                severity=LintSeverity.ERROR,
                code="CYCLE_DETECTED",
                message=f"Cycle detected involving nodes: {', '.join(cycle_nodes)}",
            )
        )

    return order, diagnostics


# ── Unreachable Node Detection ───────────────────────────


def find_unreachable(
    nodes: dict[str, GraphNode], edges: list[GraphEdge]
) -> list[LintDiagnostic]:
    """BFS from root nodes (no incoming edges). Flag unreachable nodes."""
    incoming: set[str] = {e.target for e in edges}
    roots = [nid for nid in nodes if nid not in incoming]

    if not roots:
        # All nodes have incoming edges - must be a cycle (handled elsewhere)
        return []

    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source].append(edge.target)

    visited: set[str] = set()
    bfs_queue: deque[str] = deque(roots)
    while bfs_queue:
        nid = bfs_queue.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        for neighbor in adjacency[nid]:
            if neighbor not in visited:
                bfs_queue.append(neighbor)

    return [
        LintDiagnostic(
            node_id=nid,
            severity=LintSeverity.WARNING,
            code="UNREACHABLE_NODE",
            message=f"Node '{nid}' is unreachable from any root",
        )
        for nid in nodes
        if nid not in visited
    ]


# ── Site Scope Validation ────────────────────────────────


def validate_site_scope(
    nodes: dict[str, GraphNode], site: str
) -> list[LintDiagnostic]:
    """Ensure no actions from a different site are mixed in."""
    diagnostics: list[LintDiagnostic] = []
    for node in nodes.values():
        action = get_action(node.action_id)
        if action and action.site not in ("*", site):
            diagnostics.append(
                LintDiagnostic(
                    node_id=node.id,
                    severity=LintSeverity.ERROR,
                    code="SITE_MISMATCH",
                    message=(
                        f"Action '{node.action_id}' belongs to site '{action.site}', "
                        f"but workflow targets '{site}'"
                    ),
                )
            )
    return diagnostics


# ── Adjacency Helpers ────────────────────────────────────


def build_adjacency(edges: list[GraphEdge]) -> dict[str, list[str]]:
    """Build forward adjacency map (all edge kinds)."""
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adj[edge.source].append(edge.target)
    return adj


def build_normal_incoming(edges: list[GraphEdge]) -> dict[str, list[str]]:
    """Build incoming map for normal (non-error) edges only."""
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.kind == EdgeKind.NORMAL:
            incoming[edge.target].append(edge.source)
    return incoming


def build_normal_outgoing(edges: list[GraphEdge]) -> dict[str, list[str]]:
    """Build outgoing map for normal (non-error) edges only."""
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.kind == EdgeKind.NORMAL:
            outgoing[edge.source].append(edge.target)
    return outgoing
