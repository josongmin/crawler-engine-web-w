import { useState, useCallback, useRef, useMemo, useEffect, type DragEvent } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type OnConnect,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { Button } from "@/shared/ui/Button";
import {
  ArrowLeft,
  Play,
  Save,
  ChevronDown,
  Loader2,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import { getNodeDef, getDefaultConfig } from "@/shared/config/workflow-nodes";
import { WorkflowNode, type WorkflowNodeData } from "./components/WorkflowNode";
import { NodePalette } from "./components/NodePalette";
import { NodeConfigPanel } from "./components/NodeConfigPanel";
import { LintPanel } from "./components/LintPanel";
import { GoldenPathPanel } from "./components/GoldenPathPanel";
import { INTENTS } from "./utils/intents";
import { RunOverlay } from "./components/RunOverlay";
import { useWorkflowStore } from "@/entities/workflow/model/store";
import { api } from "@/shared/api/client";
import type { Workflow, CompileResult, LintResult, WorkflowRun } from "@/shared/types";

// ── Presets (use GoldenPathPanel INTENTS as source of truth) ─

interface WorkflowPreset {
  id: string;
  name: string;
  site: string;
  nodes: Node[];
  edges: Edge[];
}

const PRESETS: WorkflowPreset[] = INTENTS.map((intent) => {
  const { nodes, edges } = intent.build();
  return { id: intent.id, name: intent.name, site: intent.site, nodes, edges };
});

// ── Node types map ─────────────────────────────────────

const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode,
};

const defaultEdgeOptions: Edge = {
  id: "",
  source: "",
  target: "",
  type: "smoothstep",
  style: { strokeWidth: 2, stroke: "#3f3f46" },
  animated: false,
};

// ── Main page (wraps with provider) ────────────────────

export function WorkflowBuilderPage() {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderContent />
    </ReactFlowProvider>
  );
}

// ── Builder content ────────────────────────────────────

function WorkflowBuilderContent() {
  const { id } = useParams<{ id: string }>();
  const reactFlowInstance = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // ── Zustand selectors (granular subscriptions) ─────────
  const setLintResult = useWorkflowStore((s) => s.setLintResult);
  const setCompileResult = useWorkflowStore((s) => s.setCompileResult);
  const compileResult = useWorkflowStore((s) => s.compileResult);
  const storeIsRunning = useWorkflowStore((s) => s.isRunning);
  const storeNodeStates = useWorkflowStore((s) => s.nodeStates);
  const setStoreIsRunning = useWorkflowStore((s) => s.setIsRunning);
  const setStoreNodeStates = useWorkflowStore((s) => s.setNodeStates);
  const setActiveRun = useWorkflowStore((s) => s.setActiveRun);

  // Determine initial data from preset or empty
  const preset = PRESETS.find((p) => p.id === id);
  const initialNodes = useMemo(() => preset?.nodes ?? [], [preset]);
  const initialEdges = useMemo(() => preset?.edges ?? [], [preset]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState(preset?.name ?? "Untitled Workflow");
  const [workflowSite] = useState(preset?.site ?? "burghound");
  const [isRunning, setIsRunning] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCompiling, setIsCompiling] = useState(false);
  const [savedWorkflowId, setSavedWorkflowId] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [showGoldenPath, setShowGoldenPath] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ── Load saved workflow from API ───────────────────────
  useEffect(() => {
    if (!id || id === "new" || PRESETS.some((p) => p.id === id)) return;
    api
      .get<Workflow>(`/workflows/${id}`)
      .then((wf) => {
        setSavedWorkflowId(wf.id);
        setWorkflowName(wf.name);
        try {
          const graph = JSON.parse(wf.graph_json) as { nodes: Node[]; edges: Edge[] };
          setNodes(graph.nodes ?? []);
          setEdges(graph.edges ?? []);
          setTimeout(() => reactFlowInstance.fitView({ padding: 0.3 }), 50);
        } catch {
          /* invalid graph_json */
        }
        if (wf.compiled_json) {
          try {
            setCompileResult(JSON.parse(wf.compiled_json) as CompileResult);
          } catch {
            /* ignore */
          }
        }
      })
      .catch((err: unknown) => {
        console.error("Failed to load workflow:", err);
      });
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Build graph JSON helper ────────────────────────────
  const buildGraphJson = useCallback(() => {
    return JSON.stringify({ nodes, edges });
  }, [nodes, edges]);

  // ── Lint on graph changes (debounced) ──────────────────
  const lintTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (nodes.length === 0) {
      setLintResult(null);
      return;
    }
    if (lintTimer.current) clearTimeout(lintTimer.current);
    lintTimer.current = setTimeout(async () => {
      try {
        const result = await api.post<LintResult>("/workflows/validate", {
          graph_json: buildGraphJson(),
          site: workflowSite,
        });
        setLintResult(result);
      } catch {
        console.warn("Lint validation unavailable");
      }
    }, 500);
    return () => {
      if (lintTimer.current) clearTimeout(lintTimer.current);
    };
  }, [nodes, edges, workflowSite, buildGraphJson, setLintResult]);

  // ── Edge connection ──────────────────────────────────

  const onConnect: OnConnect = useCallback(
    (params) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: "smoothstep",
            style: { strokeWidth: 2, stroke: "#3f3f46" },
          },
          eds,
        ),
      );
    },
    [setEdges],
  );

  // ── Drag & drop from palette ─────────────────────────

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      const nodeType = e.dataTransfer.getData("application/reactflow");
      if (!nodeType) return;

      const def = getNodeDef(nodeType);
      if (!def) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });

      const newNode: Node = {
        id: `node-${Date.now()}`,
        type: "workflowNode",
        position,
        data: {
          nodeType,
          label: def.name,
          config: getDefaultConfig(nodeType),
          status: "idle",
        } satisfies WorkflowNodeData,
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes],
  );

  // ── Node config changes ──────────────────────────────

  const handleConfigChange = useCallback(
    (nodeId: string, config: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n;
          const data = n.data as WorkflowNodeData;
          const { __label, ...cleanConfig } = config;
          const label = typeof __label === "string" ? __label : data.label;
          return { ...n, data: { ...data, label, config: cleanConfig } };
        }),
      );
      setSelectedNode((sel) => {
        if (!sel || sel.id !== nodeId) return sel;
        const data = sel.data as WorkflowNodeData;
        const { __label, ...cleanConfig } = config;
        const label = typeof __label === "string" ? __label : data.label;
        return { ...sel, data: { ...data, label, config: cleanConfig } };
      });
    },
    [setNodes],
  );

  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNode(null);
    },
    [setNodes, setEdges],
  );

  const handleDuplicateNode = useCallback(
    (nodeId: string) => {
      const source = nodes.find((n) => n.id === nodeId);
      if (!source) return;
      const newNode: Node = {
        ...source,
        id: `node-${Date.now()}`,
        position: { x: source.position.x + 30, y: source.position.y + 30 },
        selected: false,
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes, setNodes],
  );

  // ── Load preset ──────────────────────────────────────

  const loadPreset = useCallback(
    (p: WorkflowPreset) => {
      setNodes(p.nodes);
      setEdges(p.edges);
      setWorkflowName(p.name);
      setSelectedNode(null);
      setShowPresets(false);
      setTimeout(() => reactFlowInstance.fitView({ padding: 0.3 }), 50);
    },
    [setNodes, setEdges, reactFlowInstance],
  );

  // ── Golden path intent handler ────────────────────────

  const handleGoldenPathSelect = useCallback(
    (newNodes: Node[], newEdges: Edge[], name: string) => {
      setNodes(newNodes);
      setEdges(newEdges);
      setWorkflowName(name);
      setSelectedNode(null);
      setTimeout(() => reactFlowInstance.fitView({ padding: 0.3 }), 50);
    },
    [setNodes, setEdges, reactFlowInstance],
  );

  // ── Save workflow ─────────────────────────────────────

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setErrorMsg(null);
    try {
      const graphJson = buildGraphJson();
      if (savedWorkflowId) {
        await api.put(`/workflows/${savedWorkflowId}`, {
          name: workflowName,
          graph_json: graphJson,
        });
      } else {
        const wf = await api.post<Workflow>("/workflows", {
          name: workflowName,
          site: workflowSite,
          graph_json: graphJson,
        });
        setSavedWorkflowId(wf.id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Save failed";
      setErrorMsg(msg);
    } finally {
      setIsSaving(false);
    }
  }, [buildGraphJson, workflowName, workflowSite, savedWorkflowId]);

  // ── Compile workflow ──────────────────────────────────

  const handleCompile = useCallback(async () => {
    setErrorMsg(null);
    // Snapshot graph state at call time to prevent race conditions
    const graphJson = buildGraphJson();
    let wfId = savedWorkflowId;

    if (!wfId) {
      // Auto-save first
      setIsSaving(true);
      try {
        const wf = await api.post<Workflow>("/workflows", {
          name: workflowName,
          site: workflowSite,
          graph_json: graphJson,
        });
        wfId = wf.id;
        setSavedWorkflowId(wf.id);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Auto-save failed";
        setErrorMsg(msg);
        setIsSaving(false);
        return;
      } finally {
        setIsSaving(false);
      }
    } else {
      // Save latest graph before compiling
      try {
        await api.put(`/workflows/${wfId}`, {
          name: workflowName,
          graph_json: graphJson,
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Pre-compile save failed";
        setErrorMsg(msg);
        return;
      }
    }

    setIsCompiling(true);
    try {
      const result = await api.post<CompileResult>(`/workflows/${wfId}/compile`);
      setCompileResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Compile failed";
      setErrorMsg(msg);
    } finally {
      setIsCompiling(false);
    }
  }, [savedWorkflowId, buildGraphJson, workflowName, workflowSite, setCompileResult]);

  // ── Run workflow ──────────────────────────────────────

  const handleRun = useCallback(async () => {
    setErrorMsg(null);

    // Compile if needed
    if (!compileResult?.valid || !savedWorkflowId) {
      await handleCompile();
    }

    // Re-read from store after compile
    const latestCompileResult = useWorkflowStore.getState().compileResult;
    const wfId = savedWorkflowId ?? useWorkflowStore.getState().activeWorkflow?.id;
    if (!wfId || !latestCompileResult?.valid) return;

    setIsRunning(true);
    setStoreIsRunning(true);
    setStoreNodeStates({});

    // Reset node statuses
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: "idle" } })));

    try {
      const run = await api.post<WorkflowRun>(`/workflows/${wfId}/run`);
      setRunId(run.id);
      setActiveRun(run);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Run failed to start";
      setErrorMsg(msg);
      setIsRunning(false);
      setStoreIsRunning(false);
    }
  }, [savedWorkflowId, compileResult, handleCompile, setNodes, setStoreIsRunning, setStoreNodeStates, setActiveRun]);

  // ── Update node visuals from store nodeStates ─────────
  useEffect(() => {
    if (!storeIsRunning && Object.keys(storeNodeStates).length === 0) return;
    setNodes((nds) =>
      nds.map((n) => {
        const newStatus = storeNodeStates[n.id];
        if (!newStatus) return n;
        return { ...n, data: { ...n.data, status: newStatus } };
      }),
    );
  }, [storeNodeStates, storeIsRunning, setNodes]);

  const handleRunComplete = useCallback(() => {
    setIsRunning(false);
    setRunId(null);
  }, []);

  // ── Render ───────────────────────────────────────────

  const lintResult = useWorkflowStore((s) => s.lintResult);
  const lintDiags = lintResult?.diagnostics ?? [];
  const hasErrors = lintDiags.some((d) => d.severity === "error");

  return (
    <div className="-m-6 flex h-[calc(100vh-3.5rem)] flex-col">
      {/* ── Toolbar ────────────────────────────────── */}
      <div className="border-border bg-surface-0 flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-3">
          <Link
            to="/workflows"
            className="text-fg-subtle hover:bg-surface-100 hover:text-fg-tertiary rounded-md p-1.5 transition-colors"
          >
            <ArrowLeft size={16} />
          </Link>
          <div className="bg-border h-5 w-px" />
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-fg-secondary placeholder:text-fg-faint focus:text-fg bg-transparent text-sm font-semibold outline-none"
            placeholder="Workflow name..."
          />
          <span className="bg-surface-200 text-fg-subtle rounded px-1.5 py-0.5 text-[10px]">
            {nodes.length} nodes · {edges.length} edges
          </span>
          {lintDiags.length > 0 && (
            <span className="flex items-center gap-1">
              {hasErrors ? (
                <AlertTriangle size={12} className="text-status-danger" />
              ) : (
                <CheckCircle2 size={12} className="text-status-success" />
              )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Preset dropdown */}
          <div className="relative">
            <Button
              size="sm"
              icon={<ChevronDown size={12} />}
              onClick={() => setShowPresets(!showPresets)}
            >
              Presets
            </Button>
            {showPresets && (
              <div className="border-border bg-surface-50 absolute top-full right-0 z-50 mt-1 w-64 rounded-lg border py-1 shadow-xl">
                {PRESETS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => loadPreset(p)}
                    className="hover:bg-surface-100 flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors"
                  >
                    <span className="text-fg-secondary text-xs font-medium">{p.name}</span>
                    <span className="text-fg-subtle text-[10px]">
                      {p.site} · {p.nodes.length} nodes
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button
            size="sm"
            icon={<Sparkles size={13} />}
            onClick={() => setShowGoldenPath(!showGoldenPath)}
          >
            Compile
          </Button>
          <Button
            size="sm"
            variant="primary"
            icon={isRunning ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            onClick={() => void handleRun()}
            disabled={isRunning || nodes.length === 0}
          >
            {isRunning ? "Running..." : "Run"}
          </Button>
          <Button size="sm" icon={<Save size={13} />} onClick={() => void handleSave()} loading={isSaving}>
            Save
          </Button>
        </div>
      </div>

      {/* ── Error banner ─────────────────────────────── */}
      {errorMsg && (
        <div className="bg-status-danger-muted text-status-danger flex items-center justify-between px-4 py-1.5 text-xs">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="hover:underline text-[10px]">
            Dismiss
          </button>
        </div>
      )}

      {/* ── Main area ──────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: palette */}
        <NodePalette />

        {/* Center: canvas + lint panel */}
        <div className="flex flex-1 flex-col">
          <div className="flex-1" ref={reactFlowWrapper}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onDrop={onDrop}
              onDragOver={onDragOver}
              nodeTypes={nodeTypes}
              defaultEdgeOptions={defaultEdgeOptions}
              onNodeClick={(_, node) => setSelectedNode(node)}
              onPaneClick={() => {
                setSelectedNode(null);
                setShowPresets(false);
              }}
              colorMode="dark"
              fitView
              fitViewOptions={{ padding: 0.3 }}
              proOptions={{ hideAttribution: true }}
              className="workflow-canvas"
            >
              <Background gap={20} size={1} color="#27272a" />
              <MiniMap
                nodeStrokeColor="#3f3f46"
                nodeColor="#18181b"
                maskColor="rgba(0,0,0,0.6)"
                className="!border-border !bg-surface-0 !rounded-lg !border"
              />
              <Controls className="!border-border !bg-surface-50 [&>button]:!border-border [&>button]:!bg-surface-50 [&>button]:!text-fg-muted [&>button:hover]:!bg-surface-100 [&>button:hover]:!text-fg-secondary !rounded-lg !border" />
            </ReactFlow>
          </div>

          {/* Bottom: lint diagnostics */}
          <LintPanel diagnostics={lintDiags} />
        </div>

        {/* Right: config or compile/golden-path panel */}
        {selectedNode ? (
          <NodeConfigPanel
            node={selectedNode}
            onConfigChange={handleConfigChange}
            onDelete={handleDeleteNode}
            onDuplicate={handleDuplicateNode}
          />
        ) : showGoldenPath ? (
          <div className="border-border bg-surface-0 w-64 overflow-y-auto border-l">
            <div className="border-border border-b px-4 py-3">
              <h3 className="text-fg-tertiary text-xs font-semibold">Compile & Intents</h3>
            </div>
            <div className="p-3">
              {/* Compile button */}
              <button
                onClick={() => void handleCompile()}
                disabled={isCompiling || nodes.length === 0}
                className="bg-accent-500/10 text-accent-fg hover:bg-accent-500/20 disabled:opacity-40 mb-4 flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors"
              >
                {isCompiling ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Sparkles size={12} />
                )}
                {isCompiling ? "Compiling..." : "Compile DAG"}
              </button>

              {/* Compile result */}
              {compileResult && (
                <div className="mb-4">
                  <div
                    className={`mb-2 rounded-lg px-3 py-2 text-center text-xs font-medium ${
                      compileResult.valid
                        ? "bg-status-success-muted text-status-success"
                        : "bg-status-danger-muted text-status-danger"
                    }`}
                  >
                    {compileResult.valid ? "Valid" : "Invalid"} —{" "}
                    {compileResult.nodes.length} nodes
                    {compileResult.auto_inserted_nodes.length > 0 && (
                      <span className="text-fg-subtle block text-[10px]">
                        +{compileResult.auto_inserted_nodes.length} auto-inserted
                      </span>
                    )}
                  </div>

                  {compileResult.valid && (
                    <div className="space-y-1">
                      <p className="text-fg-faint mb-1 text-[10px] font-semibold uppercase tracking-wider">
                        Execution Order
                      </p>
                      {compileResult.nodes.map((node, i) => {
                        const shortType = node.action_id.split(".").slice(1).join(".");
                        const def = getNodeDef(shortType);
                        const Icon = def?.icon;
                        return (
                          <div
                            key={node.node_id}
                            className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] ${
                              node.auto_inserted ? "border-accent-500/20 border border-dashed" : ""
                            }`}
                          >
                            <span className="text-fg-faint w-3 text-right font-mono text-[9px]">
                              {i + 1}
                            </span>
                            {Icon && (
                              <div className={`rounded p-1 ${def?.colorClass ?? ""}`}>
                                <Icon size={10} strokeWidth={2} />
                              </div>
                            )}
                            <span className="text-fg-secondary truncate font-medium">
                              {def?.name ?? shortType}
                            </span>
                            {node.auto_inserted && (
                              <span className="text-accent-fg text-[9px]">auto</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Quick start intents */}
              <GoldenPathPanel onSelect={handleGoldenPathSelect} />
            </div>
          </div>
        ) : null}
      </div>

      {/* Run WebSocket overlay */}
      {runId && <RunOverlay runId={runId} onComplete={handleRunComplete} />}
    </div>
  );
}
