import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Select } from "@/shared/ui/Select";
import { getNodeDef, type ConfigField } from "@/shared/config/workflow-nodes";
import { Trash2, Copy } from "lucide-react";
import { clsx } from "clsx";
import type { Node } from "@xyflow/react";

// ── Types ──────────────────────────────────────────────

interface Props {
  node: Node;
  onConfigChange: (nodeId: string, config: Record<string, unknown>) => void;
  onDelete: (nodeId: string) => void;
  onDuplicate: (nodeId: string) => void;
}

// ── Component ──────────────────────────────────────────

export function NodeConfigPanel({
  node,
  onConfigChange,
  onDelete,
  onDuplicate,
}: Props) {
  const data = node.data as {
    nodeType: string;
    label: string;
    config: Record<string, unknown>;
    status: string;
  };

  const def = getNodeDef(data.nodeType);
  if (!def) return null;

  const Icon = def.icon;

  const handleFieldChange = (key: string, value: unknown) => {
    onConfigChange(node.id, { ...data.config, [key]: value });
  };

  return (
    <div className="flex w-72 flex-col border-l border-border bg-surface-0 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className={clsx("rounded-lg p-1.5", def.colorClass)}>
            <Icon size={14} strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold text-fg-secondary">
              {data.label}
            </h3>
            <p className="text-[10px] text-fg-subtle">{def.category}</p>
          </div>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-fg-subtle">
          {def.description}
        </p>
      </div>

      {/* Config fields */}
      <div className="flex-1 space-y-4 p-4">
        {/* Node label */}
        <Input
          label="Label"
          value={data.label}
          onChange={(e) => {
            /* label change is handled by parent via onConfigChange with special key */
            onConfigChange(node.id, {
              ...data.config,
              __label: e.target.value,
            });
          }}
          className="text-xs"
        />

        {/* Dynamic config fields */}
        {def.configFields.map((field) => (
          <FieldRenderer
            key={field.key}
            field={field}
            value={data.config[field.key] ?? field.default}
            onChange={(v) => handleFieldChange(field.key, v)}
          />
        ))}

        {def.configFields.length === 0 && (
          <p className="text-xs text-fg-faint">
            No configuration needed for this node.
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            icon={<Copy size={12} />}
            onClick={() => onDuplicate(node.id)}
            className="flex-1"
          >
            Duplicate
          </Button>
          <Button
            size="sm"
            variant="danger"
            icon={<Trash2 size={12} />}
            onClick={() => onDelete(node.id)}
            className="flex-1"
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Field renderer ─────────────────────────────────────

function FieldRenderer({
  field,
  value,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  switch (field.type) {
    case "text":
      return (
        <Input
          label={field.label}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="font-mono text-xs"
        />
      );

    case "number":
      return (
        <Input
          label={field.label}
          type="number"
          value={String(value ?? 0)}
          onChange={(e) => onChange(Number(e.target.value))}
          className="text-xs"
        />
      );

    case "boolean":
      return (
        <label className="flex items-center justify-between gap-3">
          <span className="text-xs font-medium text-fg-muted">
            {field.label}
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(value)}
            onClick={() => onChange(!value)}
            className={clsx(
              "relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors",
              value ? "bg-accent-500" : "bg-surface-300",
            )}
          >
            <span
              className={clsx(
                "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transition-transform",
                value ? "translate-x-4" : "translate-x-0",
              )}
            />
          </button>
        </label>
      );

    case "select":
      return (
        <Select
          label={field.label}
          options={field.options ?? []}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          className="text-xs"
        />
      );

    default:
      return null;
  }
}
