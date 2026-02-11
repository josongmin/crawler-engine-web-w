import { Link } from "react-router-dom";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Plus, FileCode2 } from "lucide-react";

const mockRules = [
  {
    id: "r1",
    name: "search-results",
    page_type: "search",
    version: 3,
    project: "burghound-full-db",
    is_active: true,
    fields: 5,
    updated: "2h ago",
  },
  {
    id: "r2",
    name: "wine-detail",
    page_type: "detail",
    version: 2,
    project: "burghound-full-db",
    is_active: true,
    fields: 5,
    updated: "1d ago",
  },
  {
    id: "r3",
    name: "producer-list",
    page_type: "list",
    version: 1,
    project: "burghound-full-db",
    is_active: true,
    fields: 3,
    updated: "3d ago",
  },
];

export function RulesPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-fg-subtle text-sm">Declarative extraction rules for each page type</p>
        </div>
        <Button variant="primary" icon={<Plus size={14} />}>
          New Rule
        </Button>
      </div>

      <div className="space-y-3">
        {mockRules.map((r) => (
          <Link key={r.id} to={`/rules/${r.id}`}>
            <Card hover className="hover:border-accent-500/30 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="bg-surface-100 text-fg-muted rounded-lg p-2">
                    <FileCode2 size={18} strokeWidth={1.6} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-fg text-sm font-semibold">{r.name}</span>
                      <span className="bg-surface-200 text-fg-subtle rounded px-1.5 py-0.5 font-mono text-[10px]">
                        v{r.version}
                      </span>
                    </div>
                    <div className="text-fg-subtle mt-0.5 flex items-center gap-3 text-xs">
                      <span>{r.page_type}</span>
                      <span>{r.fields} fields</span>
                      <span>{r.project}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-fg-faint text-xs">{r.updated}</span>
                  <StatusBadge status={r.is_active ? "active" : "inactive"} />
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
