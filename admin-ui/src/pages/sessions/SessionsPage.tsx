import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { LogIn, LogOut, RefreshCw, Trash2 } from "lucide-react";

const mockSessions = [
  {
    site: "burghound",
    status: "active" as const,
    ttl_remaining: "2d 14h",
    ttl_pct: 68,
    use_count: 23,
    last_login: "2h ago",
    user_agent: "Chrome/144.0 on macOS",
    clean_close: true,
  },
];

export function SessionsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {mockSessions.map((s) => (
        <Card key={s.site} hover>
          <div className="flex items-start justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-fg">{s.site}</h2>
                <StatusBadge status={s.status} />
              </div>

              {/* TTL Bar */}
              <div className="w-80 space-y-1">
                <div className="flex justify-between text-xs text-fg-subtle">
                  <span>TTL Remaining</span>
                  <span>{s.ttl_remaining}</span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-200">
                  <div
                    className="h-full rounded-full bg-status-success/60 transition-all"
                    style={{ width: `${s.ttl_pct}%` }}
                  />
                </div>
              </div>

              {/* Meta */}
              <div className="flex gap-6 text-xs text-fg-subtle">
                <span>Uses: {s.use_count}</span>
                <span>Last login: {s.last_login}</span>
                <span>Clean close: {s.clean_close ? "yes" : "no"}</span>
              </div>

              {/* Persona */}
              <div className="rounded-lg bg-surface-0 px-3 py-2 font-mono text-xs text-fg-muted">
                {s.user_agent}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2">
              <Button size="sm" variant="primary" icon={<LogIn size={14} />}>
                Login
              </Button>
              <Button size="sm" icon={<LogOut size={14} />}>
                Logout
              </Button>
              <Button size="sm" icon={<RefreshCw size={14} />}>
                Refresh
              </Button>
              <Button size="sm" variant="danger" icon={<Trash2 size={14} />}>
                Clear
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
