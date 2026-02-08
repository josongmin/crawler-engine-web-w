import { useState, useCallback, useRef, useMemo, type DragEvent } from "react";
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
import { Input } from "@/shared/ui/Input";
import {
  ArrowLeft,
  Play,
  Save,
  ChevronDown,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { clsx } from "clsx";

import { getNodeDef, getDefaultConfig } from "@/shared/config/workflow-nodes";
import {
  WorkflowNode,
  type WorkflowNodeData,
} from "./components/WorkflowNode";
import { NodePalette } from "./components/NodePalette";
import { NodeConfigPanel } from "./components/NodeConfigPanel";

// ── Presets ────────────────────────────────────────────

interface WorkflowPreset {
  id: string;
  name: string;
  site: string;
  nodes: Node[];
  edges: Edge[];
}

function makeNode(
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

function makeEdge(
  source: string,
  target: string,
  sourceHandle = "output",
): Edge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
    sourceHandle,
    type: "smoothstep",
    animated: false,
  };
}

const PRESETS: WorkflowPreset[] = [
  {
    id: "full-crawl",
    name: "Full Crawl Pipeline",
    site: "burghound",
    nodes: [
      makeNode("n1", "login", 250, 25),
      makeNode("n2", "search", 250, 175, { limit: 50, ruleId: "r1" }),
      makeNode("n3", "detail", 250, 325, { ruleId: "r2" }),
      makeNode("n4", "save-file", 250, 475, { format: "json" }),
    ],
    edges: [makeEdge("n1", "n2"), makeEdge("n2", "n3"), makeEdge("n3", "n4")],
  },
  {
    id: "quick-export",
    name: "Quick Kit Export",
    site: "burghound",
    nodes: [
      makeNode("n1", "login", 250, 25),
      makeNode("n2", "export-curl", 250, 175, {
        baseUrl: "https://www.burghound.com/tnsearch/tasting_notes.php",
        minimalHeaders: true,
      }),
    ],
    edges: [makeEdge("n1", "n2")],
  },
  {
    id: "review-pipeline",
    name: "Review Pipeline",
    site: "vivino",
    nodes: [
      makeNode("n1", "login", 250, 25),
      makeNode("n2", "search", 250, 175, { limit: 100 }),
      makeNode("n3", "review", 250, 325, { limit: 50 }),
      makeNode("n4", "save-file", 250, 475, { format: "jsonl" }),
    ],
    edges: [makeEdge("n1", "n2"), makeEdge("n2", "n3"), makeEdge("n3", "n4")],
  },
  {
    id: "session-check",
    name: "Safe Session Crawl",
    site: "burghound",
    nodes: [
      makeNode("n1", "check-session", 250, 25),
      makeNode("n2", "login", 450, 175),
      makeNode("n3", "search", 250, 325, { limit: 50, ruleId: "r1" }),
      makeNode("n4", "save-file", 250, 475, { format: "json" }),
      makeNode("n5", "notify", 250, 600, {
        message: "Crawl complete",
      }),
    ],
    edges: [
      makeEdge("n1", "n3", "output"), // session OK → search
      makeEdge("n1", "n2", "error"), // session bad → login
      makeEdge("n2", "n3"),
      makeEdge("n3", "n4"),
      makeEdge("n4", "n5"),
    ],
  },
];

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

  // Determine initial data from preset or empty
  const preset = PRESETS.find((p) => p.id === id);
  const initialNodes = useMemo(() => preset?.nodes ?? [], [preset]);
  const initialEdges = useMemo(() => preset?.edges ?? [], [preset]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [workflowName, setWorkflowName] = useState(
    preset?.name ?? "Untitled Workflow",
  );
  const [isRunning, setIsRunning] = useState(false);
  const [showPresets, setShowPresets] = useState(false);

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

          // Handle special __label key
          const label =
            typeof config.__label === "string" ? config.__label : data.label;
          const { __label: _, ...cleanConfig } = config;

          return {
            ...n,
            data: { ...data, label, config: cleanConfig },
          };
        }),
      );
      // Keep selected node in sync
      setSelectedNode((sel) => {
        if (!sel || sel.id !== nodeId) return sel;
        const data = sel.data as WorkflowNodeData;
        const label =
          typeof config.__label === "string" ? config.__label : data.label;
        const { __label: _, ...cleanConfig } = config;
        return {
          ...sel,
          data: { ...data, label, config: cleanConfig },
        };
      });
    },
    [setNodes],
  );

  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId),
      );
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
        position: {
          x: source.position.x + 30,
          y: source.position.y + 30,
        },
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

  // ── Mock run ─────────────────────────────────────────

  const handleRun = useCallback(() => {
    setIsRunning(true);
    // Simulate sequential node execution
    const orderedNodes = [...nodes];
    let delay = 0;
    orderedNodes.forEach((n, i) => {
      delay += 800 + Math.random() * 600;
      setTimeout(() => {
        setNodes((nds) =>
          nds.map((nd) =>
            nd.id === n.id
              ? { ...nd, data: { ...nd.data, status: "running" } }
              : nd,
          ),
        );
      }, delay);
      delay += 600 + Math.random() * 800;
      setTimeout(() => {
        setNodes((nds) =>
          nds.map((nd) =>
            nd.id === n.id
              ? { ...nd, data: { ...nd.data, status: "success" } }
              : nd,
          ),
        );
        if (i === orderedNodes.length - 1) {
          setIsRunning(false);
        }
      }, delay);
    });
  }, [nodes, setNodes]);

  // ── Render ───────────────────────────────────────────

  return (
    <div className="-m-6 flex h-[calc(100vh-3.5rem)] flex-col">
      {/* ── Toolbar ────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border bg-surface-0 px-4 py-2">
        <div className="flex items-center gap-3">
          <Link
            to="/workflows"
            className="rounded-md p-1.5 text-fg-subtle transition-colors hover:bg-surface-100 hover:text-fg-tertiary"
          >
            <ArrowLeft size={16} />
          </Link>
          <div className="h-5 w-px bg-border" />
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="bg-transparent text-sm font-semibold text-fg-secondary outline-none placeholder:text-fg-faint focus:text-fg"
            placeholder="Workflow name..."
          />
          <span className="rounded bg-surface-200 px-1.5 py-0.5 text-[10px] text-fg-subtle">
            {nodes.length} nodes · {edges.length} edges
          </span>
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
              <div className="absolute right-0 top-full z-50 mt-1 w-64 rounded-lg border border-border bg-surface-50 py-1 shadow-xl">
                {PRESETS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => loadPreset(p)}
                    className="flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors hover:bg-surface-100"
                  >
                    <span className="text-xs font-medium text-fg-secondary">
                      {p.name}
                    </span>
                    <span className="text-[10px] text-fg-subtle">
                      {p.site} · {p.nodes.length} nodes
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button
            size="sm"
            variant="primary"
            icon={
              isRunning ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Play size={13} />
              )
            }
            onClick={handleRun}
            disabled={isRunning || nodes.length === 0}
          >
            {isRunning ? "Running..." : "Run"}
          </Button>
          <Button size="sm" icon={<Save size={13} />}>
            Save
          </Button>
        </div>
      </div>

      {/* ── Main area ──────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: palette */}
        <NodePalette />

        {/* Center: canvas */}
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
            <Background
              gap={20}
              size={1}
              color="#27272a"
            />
            <MiniMap
              nodeStrokeColor="#3f3f46"
              nodeColor="#18181b"
              maskColor="rgba(0,0,0,0.6)"
              className="!rounded-lg !border !border-border !bg-surface-0"
            />
            <Controls
              className="!rounded-lg !border !border-border !bg-surface-50 [&>button]:!border-border [&>button]:!bg-surface-50 [&>button]:!text-fg-muted [&>button:hover]:!bg-surface-100 [&>button:hover]:!text-fg-secondary"
            />
          </ReactFlow>
        </div>

        {/* Right: config panel */}
        {selectedNode && (
          <NodeConfigPanel
            node={selectedNode}
            onConfigChange={handleConfigChange}
            onDelete={handleDeleteNode}
            onDuplicate={handleDuplicateNode}
          />
        )}
      </div>
    </div>
  );
}
