import type { Node, Edge } from "@xyflow/react";
import { getNodeDef, getDefaultConfig } from "@/shared/config/workflow-nodes";
import type { WorkflowNodeData } from "../components/WorkflowNode";

export function makeNode(
  id: string,
  nodeType: string,
  x: number,
  y: number,
  configOverrides: Record<string, unknown> = {},
): Node {
  const def = getNodeDef(nodeType);
  return {
    id,
    type: "workflowNode",
    position: { x, y },
    data: {
      nodeType,
      label: def?.name ?? nodeType,
      config: { ...getDefaultConfig(nodeType), ...configOverrides },
      status: "idle",
    } satisfies WorkflowNodeData,
  };
}

export function makeEdge(source: string, target: string, sourceHandle = "output"): Edge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
    sourceHandle,
    type: "smoothstep",
    animated: false,
  };
}
