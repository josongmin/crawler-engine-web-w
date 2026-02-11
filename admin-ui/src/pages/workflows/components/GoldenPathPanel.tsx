import type { Node, Edge } from "@xyflow/react";
import { INTENTS } from "../utils/intents";

// ── Component ──────────────────────────────────────────

interface GoldenPathPanelProps {
  onSelect: (nodes: Node[], edges: Edge[], name: string) => void;
}

export function GoldenPathPanel({ onSelect }: GoldenPathPanelProps) {
  return (
    <div className="space-y-1.5">
      <div className="text-fg-faint px-1 text-[10px] font-semibold tracking-widest uppercase">
        Quick Start
      </div>
      {INTENTS.map((intent) => {
        const Icon = intent.icon;
        return (
          <button
            key={intent.id}
            onClick={() => {
              const { nodes, edges } = intent.build();
              onSelect(nodes, edges, intent.name);
            }}
            className="hover:bg-surface-100 group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors"
          >
            <div className="bg-surface-100 group-hover:bg-surface-200 rounded-md p-1.5 transition-colors">
              <Icon size={12} className="text-fg-muted group-hover:text-accent-fg" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-fg-tertiary group-hover:text-fg truncate text-xs font-medium">
                {intent.name}
              </div>
              <div className="text-fg-faint group-hover:text-fg-subtle truncate text-[10px]">
                {intent.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
