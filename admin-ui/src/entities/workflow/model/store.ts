import { create } from "zustand";
import type {
  ActionDef,
  Workflow,
  WorkflowRun,
  LintResult,
  CompileResult,
} from "@/shared/types";
import type { NodeTypeDef } from "@/shared/config/workflow-nodes";
import type { Node, Edge } from "@xyflow/react";
import { api } from "@/shared/api/client";
import { buildNodeDefsFromCatalog } from "@/shared/config/workflow-nodes";

interface WorkflowState {
  // ── Catalog ──────────────────────────
  catalog: ActionDef[];
  catalogNodeDefs: NodeTypeDef[];
  catalogLoaded: boolean;

  // ── Active workflow ──────────────────
  activeWorkflow: Workflow | null;
  workflowName: string;
  workflowSite: string;
  isDirty: boolean;

  // ── Workflow list ────────────────────
  workflows: Workflow[];

  // ── Graph state ──────────────────────
  nodes: Node[];
  edges: Edge[];

  // ── Validation ───────────────────────
  lintResult: LintResult | null;
  compileResult: CompileResult | null;

  // ── Run ──────────────────────────────
  activeRun: WorkflowRun | null;
  nodeStates: Record<string, string>;
  isRunning: boolean;

  // ── Actions ──────────────────────────
  loadCatalog: (site?: string) => Promise<void>;
  setActiveWorkflow: (wf: Workflow | null) => void;
  setWorkflowName: (name: string) => void;
  setWorkflowSite: (site: string) => void;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  markDirty: () => void;
  setLintResult: (result: LintResult | null) => void;
  setCompileResult: (result: CompileResult | null) => void;
  setActiveRun: (run: WorkflowRun | null) => void;
  setNodeStates: (states: Record<string, string>) => void;
  setIsRunning: (running: boolean) => void;
  updateNodeStatus: (nodeId: string, status: string) => void;
  loadWorkflows: () => Promise<void>;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  catalog: [],
  catalogNodeDefs: [],
  catalogLoaded: false,
  activeWorkflow: null,
  workflowName: "Untitled Workflow",
  workflowSite: "burghound",
  isDirty: false,
  workflows: [],
  nodes: [],
  edges: [],
  lintResult: null,
  compileResult: null,
  activeRun: null,
  nodeStates: {},
  isRunning: false,

  loadCatalog: async (site) => {
    const path = site ? `/catalog?site=${site}` : "/catalog";
    const catalog = await api.get<ActionDef[]>(path);
    const catalogNodeDefs = buildNodeDefsFromCatalog(catalog);
    set({ catalog, catalogNodeDefs, catalogLoaded: true });
  },

  setActiveWorkflow: (wf) => set({ activeWorkflow: wf, isDirty: false }),
  setWorkflowName: (name) => set({ workflowName: name, isDirty: true }),
  setWorkflowSite: (site) => set({ workflowSite: site, isDirty: true }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  markDirty: () => set({ isDirty: true }),
  setLintResult: (result) => set({ lintResult: result }),
  setCompileResult: (result) => set({ compileResult: result }),
  setActiveRun: (run) => set({ activeRun: run }),
  setNodeStates: (states) => set({ nodeStates: states }),
  setIsRunning: (running) => set({ isRunning: running }),

  updateNodeStatus: (nodeId, status) =>
    set((state) => ({
      nodeStates: { ...state.nodeStates, [nodeId]: status },
    })),

  loadWorkflows: async () => {
    const workflows = await api.get<Workflow[]>("/workflows");
    set({ workflows });
  },

  reset: () =>
    set({
      activeWorkflow: null,
      workflowName: "Untitled Workflow",
      workflowSite: "burghound",
      isDirty: false,
      nodes: [],
      edges: [],
      lintResult: null,
      compileResult: null,
      activeRun: null,
      nodeStates: {},
      isRunning: false,
    }),
}));
