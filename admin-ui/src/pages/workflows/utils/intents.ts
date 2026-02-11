import { Workflow, Zap, Shield, Star } from "lucide-react";
import type { Node, Edge } from "@xyflow/react";
import { makeNode, makeEdge } from "./graph-helpers";

export interface GoldenPathIntent {
  id: string;
  name: string;
  description: string;
  icon: typeof Workflow;
  site: string;
  build: () => { nodes: Node[]; edges: Edge[] };
}

export const INTENTS: GoldenPathIntent[] = [
  {
    id: "full-crawl",
    name: "Full Crawl",
    description: "Login → Search → Detail → Save",
    icon: Workflow,
    site: "*",
    build: () => ({
      nodes: [
        makeNode("n1", "login", 250, 25),
        makeNode("n2", "search", 250, 175, { limit: 50 }),
        makeNode("n3", "detail", 250, 325),
        makeNode("n4", "save-file", 250, 475, { format: "json" }),
      ],
      edges: [makeEdge("n1", "n2"), makeEdge("n2", "n3"), makeEdge("n3", "n4")],
    }),
  },
  {
    id: "quick-export",
    name: "Quick Export",
    description: "Login → Export cURL Kit",
    icon: Zap,
    site: "*",
    build: () => ({
      nodes: [
        makeNode("n1", "login", 250, 25),
        makeNode("n2", "export-curl", 250, 175, { minimalHeaders: true }),
      ],
      edges: [makeEdge("n1", "n2")],
    }),
  },
  {
    id: "safe-session",
    name: "Safe Session Crawl",
    description: "Check → Login (if needed) → Search → Save → Notify",
    icon: Shield,
    site: "*",
    build: () => ({
      nodes: [
        makeNode("n1", "check-session", 250, 25),
        makeNode("n2", "login", 450, 175),
        makeNode("n3", "search", 250, 325, { limit: 50 }),
        makeNode("n4", "save-file", 250, 475, { format: "json" }),
        makeNode("n5", "notify", 250, 600, { message: "Crawl complete" }),
      ],
      edges: [
        makeEdge("n1", "n3", "output"),
        makeEdge("n1", "n2", "error"),
        makeEdge("n2", "n3"),
        makeEdge("n3", "n4"),
        makeEdge("n4", "n5"),
      ],
    }),
  },
  {
    id: "review-pipeline",
    name: "Review Pipeline",
    description: "Login → Search → Reviews → Save",
    icon: Star,
    site: "*",
    build: () => ({
      nodes: [
        makeNode("n1", "login", 250, 25),
        makeNode("n2", "search", 250, 175, { limit: 100 }),
        makeNode("n3", "review", 250, 325, { limit: 50 }),
        makeNode("n4", "save-file", 250, 475, { format: "jsonl" }),
      ],
      edges: [makeEdge("n1", "n2"), makeEdge("n2", "n3"), makeEdge("n3", "n4")],
    }),
  },
];
