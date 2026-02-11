import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { Dialog } from "@/shared/ui/Dialog";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Plus, Play, Trash2, ArrowRight, Workflow, Zap, Loader2, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { api } from "@/shared/api/client";
import type { Workflow as WorkflowType } from "@/shared/types";

// ── Mock data (fallback when API unavailable) ───────────

interface SavedWorkflow {
  id: string;
  name: string;
  site: string;
  nodeCount: number;
  edgeCount: number;
  nodeNames: string[];
  lastRun?: { status: string; ago: string; items?: number };
  createdAt: string;
}

const MOCK_WORKFLOWS: SavedWorkflow[] = [
  {
    id: "full-crawl",
    name: "Full Crawl Pipeline",
    site: "burghound",
    nodeCount: 4,
    edgeCount: 3,
    nodeNames: ["Login", "Search All", "Detail Extract", "Save File"],
    lastRun: { status: "success", ago: "3m", items: 142 },
    createdAt: "2026-02-07",
  },
  {
    id: "quick-export",
    name: "Quick Kit Export",
    site: "burghound",
    nodeCount: 2,
    edgeCount: 1,
    nodeNames: ["Login", "Export cURL"],
    lastRun: { status: "success", ago: "1h" },
    createdAt: "2026-02-06",
  },
  {
    id: "review-pipeline",
    name: "Review Pipeline",
    site: "vivino",
    nodeCount: 4,
    edgeCount: 3,
    nodeNames: ["Login", "Search", "Review Extract", "Save File"],
    createdAt: "2026-02-05",
  },
  {
    id: "session-check",
    name: "Safe Session Crawl",
    site: "burghound",
    nodeCount: 5,
    edgeCount: 5,
    nodeNames: ["Check Session", "Login", "Search", "Save", "Notify"],
    lastRun: { status: "success", ago: "2h", items: 50 },
    createdAt: "2026-02-04",
  },
];

interface PresetTemplate {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  icon: typeof Workflow;
}

const PRESET_TEMPLATES: PresetTemplate[] = [
  {
    id: "full-crawl",
    name: "Full Crawl",
    description: "Login → Search → Detail → Save",
    nodeCount: 4,
    icon: Workflow,
  },
  {
    id: "quick-export",
    name: "Quick Export",
    description: "Login → Export cURL Kit",
    nodeCount: 2,
    icon: Zap,
  },
  {
    id: "review-pipeline",
    name: "Review Pipeline",
    description: "Login → Search → Reviews → Save",
    nodeCount: 4,
    icon: Workflow,
  },
  {
    id: "session-check",
    name: "Safe Session",
    description: "Check → Login (if needed) → Search → Save",
    nodeCount: 5,
    icon: Workflow,
  },
];

const siteColors: Record<string, string> = {
  burghound: "bg-rose-500/20 text-rose-500 dark:text-rose-400",
  vivino: "bg-violet-500/20 text-violet-500 dark:text-violet-400",
  "wine-searcher": "bg-amber-500/20 text-amber-600 dark:text-amber-400",
};

// ── Helpers ─────────────────────────────────────────────

function parseNodeNames(graphJson: string): string[] {
  try {
    const graph = JSON.parse(graphJson) as { nodes: { data: { label: string } }[] };
    return (graph.nodes ?? []).map((n) => n.data?.label ?? "?");
  } catch {
    return [];
  }
}

function parseGraphCounts(graphJson: string): { nodeCount: number; edgeCount: number } {
  try {
    const graph = JSON.parse(graphJson) as { nodes: unknown[]; edges: unknown[] };
    return { nodeCount: graph.nodes?.length ?? 0, edgeCount: graph.edges?.length ?? 0 };
  } catch {
    return { nodeCount: 0, edgeCount: 0 };
  }
}

// ── Component ──────────────────────────────────────────

export function WorkflowsPage() {
  const [apiWorkflows, setApiWorkflows] = useState<WorkflowType[]>([]);
  const [loading, setLoading] = useState(true);
  const [useApi, setUseApi] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SavedWorkflow | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api
      .get<WorkflowType[]>("/workflows")
      .then((wfs) => {
        setApiWorkflows(wfs);
        setUseApi(true);
      })
      .catch(() => {
        /* API not available — use mock data */
      })
      .finally(() => setLoading(false));
  }, []);

  function handleDeleteClick(e: React.MouseEvent, w: SavedWorkflow) {
    e.preventDefault(); // prevent Link navigation
    e.stopPropagation();
    setDeleteTarget(w);
  }

  async function confirmDelete() {
    if (!deleteTarget || !useApi) return;
    setDeleting(true);
    try {
      await api.delete(`/workflows/${deleteTarget.id}`);
      setApiWorkflows((prev) => prev.filter((wf) => wf.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      // keep dialog open on failure so user can retry
    } finally {
      setDeleting(false);
    }
  }

  const workflowItems: SavedWorkflow[] = useApi
    ? apiWorkflows.map((wf) => {
        const { nodeCount, edgeCount } = parseGraphCounts(wf.graph_json);
        return {
          id: wf.id,
          name: wf.name,
          site: wf.site,
          nodeCount,
          edgeCount,
          nodeNames: parseNodeNames(wf.graph_json),
          createdAt: wf.created_at.slice(0, 10),
        };
      })
    : MOCK_WORKFLOWS;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-fg-subtle text-sm">
            Chain operations into reusable, one-click pipelines
          </p>
        </div>
        <Link to="/workflows/new">
          <Button variant="primary" icon={<Plus size={14} />}>
            New Workflow
          </Button>
        </Link>
      </div>

      {/* Mock data banner */}
      {!loading && !useApi && (
        <div className="border-status-warning/30 bg-status-warning/5 flex items-center gap-2 rounded-lg border px-4 py-2.5 text-xs">
          <AlertTriangle size={14} className="text-status-warning shrink-0" />
          <span className="text-fg-subtle">
            API unavailable — showing sample data
          </span>
        </div>
      )}

      {/* Saved workflows */}
      <section>
        <h2 className="text-fg-subtle mb-3 text-xs font-semibold tracking-widest uppercase">
          Saved Workflows
        </h2>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="text-fg-muted animate-spin" />
          </div>
        ) : (
          <div className="space-y-3">
            {workflowItems.length === 0 && (
              <Card>
                <p className="text-fg-subtle py-4 text-center text-sm">
                  No saved workflows yet. Create one from a template below.
                </p>
              </Card>
            )}
            {workflowItems.map((w) => (
              <Link key={w.id} to={`/workflows/${w.id}`}>
                <Card hover className="group hover:border-accent-500/30 transition-all">
                  <div className="flex items-start justify-between gap-4">
                    {/* Left info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <div className="bg-surface-100 text-fg-muted rounded-lg p-2">
                          <Workflow size={18} strokeWidth={1.6} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-fg text-sm font-semibold">{w.name}</span>
                            <span
                              className={clsx(
                                "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                                siteColors[w.site] ?? "bg-surface-200 text-fg-muted",
                              )}
                            >
                              {w.site}
                            </span>
                          </div>
                          {/* Node pipeline */}
                          <div className="text-fg-subtle mt-1 flex items-center gap-1 text-[11px]">
                            {w.nodeNames.slice(0, 5).map((name, i) => (
                              <span key={i} className="flex items-center gap-1">
                                {i > 0 && <ArrowRight size={8} className="text-border-hover" />}
                                <span>{name}</span>
                              </span>
                            ))}
                            {w.nodeNames.length > 5 && (
                              <span className="text-fg-faint">+{w.nodeNames.length - 5}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Meta */}
                      <div className="text-fg-faint mt-2.5 flex items-center gap-4 pl-12 text-[11px]">
                        <span>
                          {w.nodeCount} nodes · {w.edgeCount} edges
                        </span>
                        <span>{w.createdAt}</span>
                        {w.lastRun && (
                          <span className="flex items-center gap-1.5">
                            Last run: {w.lastRun.ago}
                            {w.lastRun.items != null && (
                              <span className="text-fg-subtle">({w.lastRun.items} items)</span>
                            )}
                            <StatusBadge status={w.lastRun.status} />
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex shrink-0 items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                      <Button size="sm" variant="primary" icon={<Play size={12} />}>
                        Run
                      </Button>
                      {useApi && (
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<Trash2 size={14} />}
                          onClick={(e) => handleDeleteClick(e, w)}
                        />
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Preset templates */}
      <section>
        <h2 className="text-fg-subtle mb-3 text-xs font-semibold tracking-widest uppercase">
          Start from Template
        </h2>
        <div className="grid grid-cols-4 gap-3">
          {PRESET_TEMPLATES.map((t) => (
            <Link key={t.id} to={`/workflows/${t.id}`}>
              <Card hover className="group hover:border-accent-500/30 text-center transition-all">
                <div className="flex flex-col items-center gap-2.5">
                  <div className="bg-surface-100 text-fg-muted group-hover:text-accent-fg rounded-lg p-3 transition-colors">
                    <t.icon size={20} strokeWidth={1.4} />
                  </div>
                  <div>
                    <div className="text-fg-secondary text-xs font-semibold">{t.name}</div>
                    <div className="text-fg-subtle mt-0.5 text-[10px]">{t.description}</div>
                  </div>
                  <span className="text-fg-faint text-[10px]">{t.nodeCount} nodes</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete Workflow"
        maxWidth="max-w-sm"
      >
        <p className="text-fg-subtle text-sm">
          Are you sure you want to delete{" "}
          <span className="text-fg font-medium">{deleteTarget?.name}</span>? This action cannot be
          undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            size="sm"
            variant="danger"
            loading={deleting}
            onClick={() => void confirmDelete()}
          >
            Delete
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
