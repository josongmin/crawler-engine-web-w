import { Link } from "react-router-dom";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import {
  Plus,
  Play,
  MoreHorizontal,
  ArrowRight,
  Workflow,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";

// ── Mock data ──────────────────────────────────────────

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

// ── Component ──────────────────────────────────────────

export function WorkflowsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-fg-subtle">
            Chain operations into reusable, one-click pipelines
          </p>
        </div>
        <Link to="/workflows/new">
          <Button variant="primary" icon={<Plus size={14} />}>
            New Workflow
          </Button>
        </Link>
      </div>

      {/* Saved workflows */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-fg-subtle">
          Saved Workflows
        </h2>
        <div className="space-y-3">
          {MOCK_WORKFLOWS.map((w) => (
            <Link key={w.id} to={`/workflows/${w.id}`}>
              <Card
                hover
                className="group transition-all hover:border-accent-500/30"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left info */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-surface-100 p-2 text-fg-muted">
                        <Workflow size={18} strokeWidth={1.6} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-fg">
                            {w.name}
                          </span>
                          <span
                            className={clsx(
                              "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                              siteColors[w.site] ??
                                "bg-surface-200 text-fg-muted",
                            )}
                          >
                            {w.site}
                          </span>
                        </div>
                        {/* Node pipeline */}
                        <div className="mt-1 flex items-center gap-1 text-[11px] text-fg-subtle">
                          {w.nodeNames.map((name, i) => (
                            <span key={i} className="flex items-center gap-1">
                              {i > 0 && (
                                <ArrowRight
                                  size={8}
                                  className="text-border-hover"
                                />
                              )}
                              <span>{name}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Meta */}
                    <div className="mt-2.5 flex items-center gap-4 pl-12 text-[11px] text-fg-faint">
                      <span>
                        {w.nodeCount} nodes · {w.edgeCount} edges
                      </span>
                      <span>{w.createdAt}</span>
                      {w.lastRun && (
                        <span className="flex items-center gap-1.5">
                          Last run: {w.lastRun.ago}
                          {w.lastRun.items != null && (
                            <span className="text-fg-subtle">
                              ({w.lastRun.items} items)
                            </span>
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
                    <Button size="sm" variant="ghost" icon={<MoreHorizontal size={14} />} />
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Preset templates */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-fg-subtle">
          Start from Template
        </h2>
        <div className="grid grid-cols-4 gap-3">
          {PRESET_TEMPLATES.map((t) => (
            <Link key={t.id} to={`/workflows/${t.id}`}>
              <Card
                hover
                className="group text-center transition-all hover:border-accent-500/30"
              >
                <div className="flex flex-col items-center gap-2.5">
                  <div className="rounded-lg bg-surface-100 p-3 text-fg-muted transition-colors group-hover:text-accent-fg">
                    <t.icon size={20} strokeWidth={1.4} />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-fg-secondary">
                      {t.name}
                    </div>
                    <div className="mt-0.5 text-[10px] text-fg-subtle">
                      {t.description}
                    </div>
                  </div>
                  <span className="text-[10px] text-fg-faint">
                    {t.nodeCount} nodes
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
