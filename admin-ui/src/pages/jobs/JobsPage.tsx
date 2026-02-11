import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Select } from "@/shared/ui/Select";
import { Plus, RotateCcw } from "lucide-react";

const mockJobs = [
  {
    id: "01JKX001",
    site: "burghound",
    rule: "search-results v3",
    status: "success" as const,
    items: 142,
    duration: "3m 12s",
    created: "2026-02-08 19:45",
  },
  {
    id: "01JKX002",
    site: "burghound",
    rule: "search-results v3",
    status: "success" as const,
    items: 89,
    duration: "2m 05s",
    created: "2026-02-08 18:30",
  },
  {
    id: "01JKX003",
    site: "burghound",
    rule: "wine-detail v2",
    status: "failed" as const,
    items: 0,
    duration: "0m 42s",
    created: "2026-02-08 17:00",
  },
  {
    id: "01JKX004",
    site: "burghound",
    rule: "search-results v2",
    status: "cancelled" as const,
    items: 34,
    duration: "1m 12s",
    created: "2026-02-08 15:00",
  },
];

export function JobsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select
            options={[
              { value: "all", label: "All Status" },
              { value: "running", label: "Running" },
              { value: "success", label: "Success" },
              { value: "failed", label: "Failed" },
            ]}
          />
          <Select
            options={[
              { value: "all", label: "All Sites" },
              { value: "burghound", label: "burghound" },
            ]}
          />
        </div>
        <Button variant="primary" icon={<Plus size={14} />}>
          New Job
        </Button>
      </div>

      <Card className="overflow-hidden p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-border text-fg-subtle border-b text-xs">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Site</th>
              <th className="px-4 py-3 font-medium">Rule</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Items</th>
              <th className="px-4 py-3 text-right font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {mockJobs.map((j) => (
              <tr
                key={j.id}
                className="border-border/50 hover:bg-surface-50 border-b transition-colors"
              >
                <td className="text-fg-muted px-4 py-3 font-mono text-xs">{j.id.slice(-4)}</td>
                <td className="text-fg-secondary px-4 py-3">{j.site}</td>
                <td className="px-4 py-3">
                  <span className="bg-surface-200 text-fg-muted rounded px-1.5 py-0.5 font-mono text-[10px]">
                    {j.rule}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={j.status} />
                </td>
                <td className="text-fg-tertiary px-4 py-3 text-right font-mono text-xs">
                  {j.items}
                </td>
                <td className="text-fg-subtle px-4 py-3 text-right font-mono text-xs">
                  {j.duration}
                </td>
                <td className="text-fg-subtle px-4 py-3 text-xs">{j.created}</td>
                <td className="px-4 py-3">
                  <Button size="sm" variant="ghost" icon={<RotateCcw size={12} />}>
                    Rerun
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
