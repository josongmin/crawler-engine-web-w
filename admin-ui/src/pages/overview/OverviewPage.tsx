import { Link } from "react-router-dom";
import { Card } from "@/shared/ui/Card";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Globe, Play, Database, ArrowRight, ExternalLink } from "lucide-react";
import { clsx } from "clsx";
import { SITES } from "@/shared/config/sites";

// ═══════════════════════════════════════════════════════
// Mock Data
// ═══════════════════════════════════════════════════════

interface SiteStatus {
  sessionStatus: "active" | "inactive" | "expired";
  ttl?: string;
  operations: number;
  lastJob?: {
    id: string;
    operation: string;
    status: string;
    items: number;
    ago: string;
  };
}

const MOCK_STATUS: Record<string, SiteStatus> = {
  burghound: {
    sessionStatus: "active",
    ttl: "2d 14h",
    operations: 2,
    lastJob: {
      id: "#47",
      operation: "search-all",
      status: "success",
      items: 142,
      ago: "3m",
    },
  },
  vivino: {
    sessionStatus: "inactive",
    operations: 3,
  },
  "wine-searcher": {
    sessionStatus: "expired",
    operations: 3,
    lastJob: {
      id: "#44",
      operation: "search",
      status: "success",
      items: 200,
      ago: "2d",
    },
  },
};

const globalStats = [
  {
    label: "Active Sessions",
    value: "1",
    sub: `/ ${SITES.length} sites`,
    icon: Globe,
    color: "text-status-success",
  },
  {
    label: "Running Jobs",
    value: "0",
    icon: Play,
    color: "text-status-info",
  },
  {
    label: "Total Items",
    value: "2,847",
    icon: Database,
    color: "text-accent-fg",
  },
];

const recentActivity = [
  {
    id: "#47",
    site: "burghound",
    operation: "search-all",
    status: "success",
    items: 142,
    ago: "3m",
  },
  {
    id: "#46",
    site: "burghound",
    operation: "search-all",
    status: "success",
    items: 89,
    ago: "1h",
  },
  {
    id: "#45",
    site: "burghound",
    operation: "wine-detail",
    status: "failed",
    items: 0,
    ago: "2h",
  },
  {
    id: "#44",
    site: "wine-searcher",
    operation: "search",
    status: "success",
    items: 200,
    ago: "2d",
  },
];

// ═══════════════════════════════════════════════════════
// OverviewPage — Cross-site dashboard
// ═══════════════════════════════════════════════════════

const siteBgMap: Record<string, string> = {
  rose: "bg-rose-500/20 text-rose-500 dark:text-rose-400",
  violet: "bg-violet-500/20 text-violet-500 dark:text-violet-400",
  amber: "bg-amber-500/20 text-amber-600 dark:text-amber-400",
};

const sessionDotMap: Record<string, string> = {
  active: "bg-status-success",
  inactive: "bg-surface-400",
  expired: "bg-status-danger",
};

export function OverviewPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* ── Global Stats ────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        {globalStats.map((s) => (
          <Card key={s.label} hover>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-fg-subtle text-xs font-medium">{s.label}</p>
                <div className="mt-1 flex items-baseline gap-1.5">
                  <p className="text-fg text-2xl font-bold">{s.value}</p>
                  {s.sub && <span className="text-fg-faint text-xs">{s.sub}</span>}
                </div>
              </div>
              <div className={`bg-surface-100 rounded-lg p-2.5 ${s.color}`}>
                <s.icon size={20} strokeWidth={1.6} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* ── Site Cards ──────────────────────────────── */}
      <div>
        <h2 className="text-fg-subtle mb-3 text-xs font-semibold tracking-widest uppercase">
          Sites
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {SITES.map((site) => {
            const info = MOCK_STATUS[site.id] ?? {
              sessionStatus: "inactive" as const,
              operations: site.operations.length,
            };

            return (
              <Link key={site.id} to={`/sites/${site.id}`}>
                <Card hover className="group hover:border-accent-500/30 transition-all">
                  {/* Header row */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={clsx(
                          "flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold",
                          siteBgMap[site.themeColor] ?? "bg-accent-500/20 text-accent-fg",
                        )}
                      >
                        {site.name[0]}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-fg text-sm font-semibold">{site.name}</span>
                          <span
                            className={clsx(
                              "h-2 w-2 rounded-full",
                              sessionDotMap[info.sessionStatus],
                            )}
                          />
                        </div>
                        <span className="text-fg-subtle text-[11px]">{site.domain}</span>
                      </div>
                    </div>
                    <ArrowRight
                      size={14}
                      className="text-fg-faint group-hover:text-accent-fg mt-1 transition-transform group-hover:translate-x-0.5"
                    />
                  </div>

                  {/* Status info */}
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <StatusBadge status={info.sessionStatus} />
                      {info.ttl && (
                        <span className="text-fg-subtle text-[11px]">TTL {info.ttl}</span>
                      )}
                    </div>

                    {/* Last job */}
                    {info.lastJob ? (
                      <div className="bg-surface-0 flex items-center gap-2 rounded-md px-2.5 py-1.5 text-[11px]">
                        <span className="text-fg-subtle font-mono">{info.lastJob.id}</span>
                        <span className="bg-surface-200 text-fg-subtle rounded px-1 py-0.5 font-mono text-[10px]">
                          {info.lastJob.operation}
                        </span>
                        <span className="text-fg-faint ml-auto">{info.lastJob.ago}</span>
                        <StatusBadge status={info.lastJob.status} />
                      </div>
                    ) : (
                      <p className="text-fg-faint text-[11px]">No recent jobs — click to set up</p>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="border-border/50 text-fg-faint mt-3 flex items-center justify-between border-t pt-2.5 text-[11px]">
                    <span>{info.operations} operations</span>
                    <span className="text-fg-subtle group-hover:text-accent-fg flex items-center gap-1">
                      Open hub
                      <ExternalLink size={10} />
                    </span>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── Recent Activity (Global) ────────────────── */}
      <Card>
        <h3 className="text-fg-tertiary mb-4 text-sm font-semibold">Recent Activity</h3>
        <div className="space-y-2">
          {recentActivity.map((j) => (
            <div
              key={j.id + j.site}
              className="bg-surface-0 flex items-center justify-between rounded-lg px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <span className="text-fg-subtle font-mono text-xs">{j.id}</span>
                <span className="text-fg-secondary text-sm font-medium">{j.site}</span>
                <span className="bg-surface-200 text-fg-muted rounded px-1.5 py-0.5 font-mono text-[10px]">
                  {j.operation}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {j.items > 0 && (
                  <span className="text-fg-subtle font-mono text-xs">{j.items} items</span>
                )}
                <StatusBadge status={j.status} />
                <span className="text-fg-faint text-xs">{j.ago}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
