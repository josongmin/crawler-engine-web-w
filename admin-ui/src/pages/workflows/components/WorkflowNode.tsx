import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { clsx } from "clsx";
import { getNodeDef } from "@/shared/config/workflow-nodes";

// ── Types ──────────────────────────────────────────────

export interface WorkflowNodeData {
  nodeType: string;
  label: string;
  config: Record<string, unknown>;
  status: "idle" | "running" | "success" | "error" | "skipped";
  [key: string]: unknown;
}

// ── Status styling ─────────────────────────────────────

const statusDot: Record<string, string> = {
  idle: "bg-surface-400",
  running: "bg-status-info animate-pulse",
  success: "bg-status-success",
  error: "bg-status-danger",
  skipped: "bg-fg-subtle",
};

const statusBorder: Record<string, string> = {
  idle: "",
  running: "border-status-info/40 shadow-status-info/10 shadow-lg",
  success: "border-status-success/30",
  error: "border-status-danger/30",
  skipped: "opacity-60",
};

// ── Handle styles ──────────────────────────────────────

const handleBase =
  "!h-2.5 !w-2.5 !rounded-full !border-2 !border-surface-400 !bg-surface-200 hover:!border-accent-500 hover:!bg-accent-500/30 transition-colors";

const errorHandleBase =
  "!h-2.5 !w-2.5 !rounded-full !border-2 !border-red-700 !bg-red-500/20 hover:!border-red-500 transition-colors";

// ── Component ──────────────────────────────────────────

export const WorkflowNode = memo(function WorkflowNode(props: NodeProps) {
  const data = props.data as WorkflowNodeData;
  const selected = props.selected;

  const def = getNodeDef(data.nodeType);
  if (!def) return null;

  const Icon = def.icon;

  // Build config summary (show key values)
  const configEntries = Object.entries(data.config).filter(
    ([, v]) => v !== "" && v !== undefined && v !== null,
  );

  return (
    <>
      {/* Input handle */}
      {def.hasInput && <Handle type="target" position={Position.Top} className={handleBase} />}

      {/* Node body */}
      <div
        className={clsx(
          "bg-surface-50 w-[220px] rounded-xl border transition-all",
          selected ? "border-accent-500 ring-accent-500/20 ring-2" : "border-border",
          statusBorder[data.status],
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2.5 px-3 py-2.5">
          <div className={clsx("rounded-lg p-1.5", def.colorClass)}>
            <Icon size={14} strokeWidth={2} />
          </div>
          <span className="text-fg-secondary truncate text-xs font-semibold">{data.label}</span>
        </div>

        {/* Config summary */}
        {configEntries.length > 0 && (
          <div className="border-border/40 text-fg-subtle border-t px-3 py-2 text-[10px] leading-4">
            {configEntries.slice(0, 3).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <span className="text-fg-faint">{k}</span>
                <span className="text-fg-muted truncate">
                  {typeof v === "boolean" ? (v ? "yes" : "no") : String(v)}
                </span>
              </div>
            ))}
            {configEntries.length > 3 && (
              <span className="text-fg-faint">+{configEntries.length - 3} more</span>
            )}
          </div>
        )}

        {/* Status bar */}
        <div className="border-border/40 flex items-center gap-1.5 border-t px-3 py-1.5">
          <span className={clsx("h-1.5 w-1.5 rounded-full", statusDot[data.status])} />
          <span className="text-fg-subtle text-[10px] font-medium">{data.status}</span>
        </div>
      </div>

      {/* Output handle */}
      {def.hasOutput && (
        <Handle type="source" position={Position.Bottom} id="output" className={handleBase} />
      )}

      {/* Error output handle (right side) */}
      {def.hasErrorOutput && (
        <Handle
          type="source"
          position={Position.Right}
          id="error"
          className={errorHandleBase}
          style={{ top: "50%" }}
        />
      )}
    </>
  );
});
