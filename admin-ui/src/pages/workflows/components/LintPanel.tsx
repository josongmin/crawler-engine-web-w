import { clsx } from "clsx";
import { AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { LintDiagnostic } from "@/shared/types";

const severityConfig = {
  error: { icon: AlertCircle, color: "text-status-danger", bg: "bg-status-danger-muted" },
  warning: { icon: AlertTriangle, color: "text-status-warning", bg: "bg-status-warning-muted" },
  info: { icon: Info, color: "text-status-info", bg: "bg-status-info-muted" },
} as const;

interface LintPanelProps {
  diagnostics: LintDiagnostic[];
  onNodeClick?: (nodeId: string) => void;
}

export function LintPanel({ diagnostics, onNodeClick }: LintPanelProps) {
  const [expanded, setExpanded] = useState(true);

  if (diagnostics.length === 0) return null;

  const errors = diagnostics.filter((d) => d.severity === "error");
  const warnings = diagnostics.filter((d) => d.severity === "warning");
  const infos = diagnostics.filter((d) => d.severity === "info");

  return (
    <div className="border-border bg-surface-0 border-t">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="hover:bg-surface-50 flex w-full items-center justify-between px-4 py-2 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-fg-tertiary text-xs font-semibold">Diagnostics</span>
          <div className="flex items-center gap-2">
            {errors.length > 0 && (
              <span className="bg-status-danger-muted text-status-danger rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                {errors.length} error{errors.length !== 1 ? "s" : ""}
              </span>
            )}
            {warnings.length > 0 && (
              <span className="bg-status-warning-muted text-status-warning rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                {warnings.length} warn
              </span>
            )}
            {infos.length > 0 && (
              <span className="bg-status-info-muted text-status-info rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                {infos.length} info
              </span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronDown size={14} className="text-fg-subtle" />
        ) : (
          <ChevronUp size={14} className="text-fg-subtle" />
        )}
      </button>

      {/* Body */}
      {expanded && (
        <div className="max-h-40 overflow-y-auto px-4 pb-2">
          <div className="space-y-1">
            {diagnostics.map((d, i) => {
              const cfg = severityConfig[d.severity as keyof typeof severityConfig] ?? severityConfig.info;
              const Icon = cfg.icon;
              return (
                <div
                  key={i}
                  className="hover:bg-surface-50 flex items-start gap-2 rounded px-2 py-1.5 transition-colors"
                >
                  <div className={clsx("mt-0.5 rounded p-0.5", cfg.bg)}>
                    <Icon size={10} className={cfg.color} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="bg-surface-200 text-fg-faint rounded px-1 py-0.5 font-mono text-[9px]">
                        {d.code}
                      </span>
                      {d.node_id && (
                        <button
                          onClick={() => onNodeClick?.(d.node_id!)}
                          className="text-accent-fg hover:underline text-[10px]"
                        >
                          {d.node_id}
                        </button>
                      )}
                    </div>
                    <p className="text-fg-subtle mt-0.5 text-[11px] leading-tight">{d.message}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
