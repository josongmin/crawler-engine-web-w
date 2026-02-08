import { useState } from "react";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import {
  Play,
  Search,
  FileText,
  MessageSquare,
  List,
  Link2,
} from "lucide-react";
import { clsx } from "clsx";
import type { SiteOperation, OperationType } from "@/shared/config/sites";
import type { LucideIcon } from "lucide-react";

// ── Icon & Color maps ──────────────────────────────────

const typeIcons: Record<OperationType, LucideIcon> = {
  search: Search,
  detail: FileText,
  review: MessageSquare,
  list: List,
};

const typeColors: Record<OperationType, string> = {
  search: "text-status-info bg-status-info-muted",
  detail: "text-status-success bg-status-success-muted",
  review: "text-violet-500 dark:text-violet-400 bg-violet-500/10",
  list: "text-status-warning bg-status-warning-muted",
};

// ── Types ──────────────────────────────────────────────

export interface LastJobInfo {
  id: string;
  status: string;
  items: number;
  ago: string;
}

interface Props {
  operation: SiteOperation;
  lastJob?: LastJobInfo;
  /** Disable the Run button (e.g. no active session) */
  disabled?: boolean;
  onRun: (operationId: string, limit: number) => void;
}

// ── Component ──────────────────────────────────────────

export function OperationCard({
  operation,
  lastJob,
  disabled,
  onRun,
}: Props) {
  const [limit, setLimit] = useState(operation.defaultLimit);

  const Icon = typeIcons[operation.type];
  const colorClass = typeColors[operation.type];

  return (
    <Card
      hover={!disabled}
      className={clsx(
        "flex flex-col justify-between",
        disabled && "opacity-50 pointer-events-none",
      )}
    >
      {/* ── Header ─────────────────────────────────── */}
      <div>
        <div className="flex items-start justify-between">
          <div className={clsx("rounded-lg p-2.5", colorClass)}>
            <Icon size={18} strokeWidth={1.6} />
          </div>
          {operation.ruleId && (
            <span className="flex items-center gap-1 rounded-md bg-surface-200 px-1.5 py-0.5 text-[10px] font-medium text-fg-subtle">
              <Link2 size={10} />
              rule linked
            </span>
          )}
        </div>
        <h3 className="mt-3 text-sm font-semibold text-fg">
          {operation.name}
        </h3>
        <p className="mt-1 text-xs leading-relaxed text-fg-subtle">
          {operation.description}
        </p>
      </div>

      {/* ── Last Job ───────────────────────────────── */}
      {lastJob && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-surface-0 px-2.5 py-2">
          <StatusBadge status={lastJob.status} />
          {lastJob.items > 0 && (
            <span className="font-mono text-[11px] text-fg-muted">
              {lastJob.items} items
            </span>
          )}
          <span className="ml-auto text-[11px] text-fg-faint">
            {lastJob.ago}
          </span>
        </div>
      )}

      {/* ── Actions ────────────────────────────────── */}
      <div className="mt-4 flex items-center gap-2 border-t border-border/50 pt-3">
        <div className="flex items-center gap-1.5">
          <label className="text-[10px] font-semibold uppercase tracking-widest text-fg-faint">
            Limit
          </label>
          <input
            type="number"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            min={1}
            max={10000}
            className="h-7 w-16 rounded-md border border-border bg-surface-0 px-2 text-center font-mono text-xs text-fg-tertiary focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/30"
          />
        </div>
        <Button
          variant="primary"
          size="sm"
          icon={<Play size={13} />}
          onClick={() => onRun(operation.id, limit)}
          disabled={disabled}
          className="ml-auto"
        >
          Run
        </Button>
      </div>
    </Card>
  );
}
