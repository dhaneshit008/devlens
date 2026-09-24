import type { GraphNode, GraphEdge } from "./types";

export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  truncated: boolean;
  commit_sha: string;
}
export interface Rule {
  id: string;
  from: string;
  allow: string[] | null;
  deny: string[] | null;
}
export interface LayerLink {
  source: string;
  target: string;
  count: number;
}
export interface ArchitectureSummary {
  commit_sha: string;
  configuration: string | null;
  direction: string;
  layers: Record<string, number>;
  relationships: LayerLink[];
  rules: Rule[];
  metrics: Record<string, number>;
}
export interface Assignment {
  node_id: string;
  path: string;
  layer: string;
  method: string;
  evidence: string[];
}
export interface Relationship {
  edge: GraphEdge;
  source: GraphNode;
  target: GraphNode;
  source_layer: string;
  target_layer: string;
  rule_ids: string[];
  status: string;
}
export interface Cycle {
  id: string;
  kind: "file" | "directory";
  members: string[];
  path: string[];
  edge_ids: string[];
}
export interface CycleDetail {
  commit_sha: string;
  cycle: Cycle;
  relationships: Relationship[];
}
