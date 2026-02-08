import { Card } from "@/shared/ui/Card";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Globe, Play, Database, FolderOpen } from "lucide-react";

const stats = [
  { label: "Active Sessions", value: "1", icon: Globe, color: "text-status-success" },
  { label: "Running Jobs", value: "0", icon: Play, color: "text-status-info" },
  { label: "Total Items", value: "2,847", icon: Database, color: "text-accent-fg" },
  { label: "Projects", value: "3", icon: FolderOpen, color: "text-violet-500 dark:text-violet-400" },
];

const recentJobs = [
  { id: "#47", site: "burghound", rule: "search-all", status: "success", items: 142, ago: "3m" },
  { id: "#46", site: "burghound", rule: "search-all", status: "success", items: 89, ago: "1h" },
  { id: "#45", site: "burghound", rule: "wine-detail", status: "failed", items: 0, ago: "2h" },
];

export function DashboardPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((s) => (
          <Card key={s.label} hover>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-fg-subtle">{s.label}</p>
                <p className="mt-1 text-2xl font-bold text-fg">{s.value}</p>
              </div>
              <div className={`rounded-lg bg-surface-100 p-2.5 ${s.color}`}>
                <s.icon size={20} strokeWidth={1.6} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-5 gap-4">
        {/* Session Health */}
        <Card className="col-span-2">
          <h3 className="mb-4 text-sm font-semibold text-fg-tertiary">Session Health</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-status-success" />
                <span className="text-sm font-medium text-fg-secondary">burghound</span>
              </div>
              <StatusBadge status="active" />
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-fg-subtle">
                <span>TTL Remaining</span>
                <span>2d 14h</span>
              </div>
              <div className="h-1.5 rounded-full bg-surface-200">
                <div className="h-full w-[68%] rounded-full bg-status-success/60" />
              </div>
            </div>
            <div className="flex gap-4 text-xs text-fg-subtle">
              <span>Uses: 23</span>
              <span>Clean close: yes</span>
              <span>Kit: exported</span>
            </div>
          </div>
        </Card>

        {/* Recent Jobs */}
        <Card className="col-span-3">
          <h3 className="mb-4 text-sm font-semibold text-fg-tertiary">Recent Jobs</h3>
          <div className="space-y-2">
            {recentJobs.map((j) => (
              <div
                key={j.id}
                className="flex items-center justify-between rounded-lg bg-surface-0 px-3 py-2.5"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-fg-subtle">{j.id}</span>
                  <span className="text-sm font-medium text-fg-secondary">{j.site}</span>
                  <span className="rounded bg-surface-200 px-1.5 py-0.5 font-mono text-[10px] text-fg-muted">
                    {j.rule}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-fg-subtle">
                    {j.items > 0 ? `${j.items} items` : "error"}
                  </span>
                  <StatusBadge status={j.status} />
                  <span className="text-xs text-fg-faint">{j.ago}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
