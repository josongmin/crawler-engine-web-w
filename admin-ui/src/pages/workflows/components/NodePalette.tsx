import { clsx } from "clsx";
import { CATEGORIES, getNodesByCategory, type NodeTypeDef } from "@/shared/config/workflow-nodes";
import type { DragEvent } from "react";

// ── Component ──────────────────────────────────────────

export function NodePalette() {
  const onDragStart = (e: DragEvent, nodeType: string) => {
    e.dataTransfer.setData("application/reactflow", nodeType);
    e.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="flex w-52 flex-col border-r border-border bg-surface-0 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-xs font-semibold text-fg-tertiary">Nodes</h3>
        <p className="mt-0.5 text-[10px] text-fg-faint">
          Drag onto the canvas
        </p>
      </div>

      {/* Categories */}
      <div className="flex-1 space-y-4 p-3">
        {CATEGORIES.map((cat) => {
          const nodes = getNodesByCategory(cat.id);
          if (nodes.length === 0) return null;
          return (
            <div key={cat.id}>
              <div
                className={clsx(
                  "mb-1.5 text-[10px] font-semibold uppercase tracking-widest",
                  cat.color,
                )}
              >
                {cat.label}
              </div>
              <div className="space-y-0.5">
                {nodes.map((node) => (
                  <PaletteItem
                    key={node.type}
                    node={node}
                    onDragStart={onDragStart}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Palette item ───────────────────────────────────────

function PaletteItem({
  node,
  onDragStart,
}: {
  node: NodeTypeDef;
  onDragStart: (e: DragEvent, type: string) => void;
}) {
  const Icon = node.icon;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, node.type)}
      className="group flex cursor-grab items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors hover:bg-surface-100 active:cursor-grabbing"
      title={node.description}
    >
      <div className={clsx("rounded-md p-1.5", node.colorClass)}>
        <Icon size={12} strokeWidth={2} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium text-fg-tertiary group-hover:text-fg">
          {node.name}
        </div>
        <div className="truncate text-[10px] text-fg-faint group-hover:text-fg-subtle">
          {node.description}
        </div>
      </div>
    </div>
  );
}
