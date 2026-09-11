export interface Evidence {
  path: string;
  start_line: number;
  end_line: number;
  method: string;
}
export interface GraphNode {
  id: string;
  kind: string;
  label: string;
  path: string;
  language: string;
  evidence: Evidence;
  is_test: boolean;
}
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  evidence: Evidence;
}
export interface Limitation {
  path: string;
  line: number;
  reason: string;
  specifier: string | null;
}
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total: number;
  offset: number;
  limit: number;
  truncated: boolean;
  commit_sha: string;
  limitations: Limitation[];
}
export interface Run {
  id: string;
  repository_url: string;
  status: string;
  stage: string;
  error: string | null;
  created_at: string;
  summary: null | {
    commit_sha: string;
    analyzer_version: string;
    languages: Record<string, number>;
    source_file_count: number;
    analyzed_bytes: number;
    skipped: Record<string, number>;
  };
}
export interface ImpactEntry {
  node: GraphNode;
  distance: number;
  classification: string;
  evidence_path: GraphEdge[];
}
export interface ImpactReport {
  target: GraphNode;
  scope: string;
  direct: ImpactEntry[];
  indirect: ImpactEntry[];
  candidate_tests: string[];
  limitations: string[];
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Check the URL or service.`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function evidenceUrl(run: Run, evidence: Evidence): string {
  return `${run.repository_url}/blob/${run.summary?.commit_sha}/${evidence.path.split("/").map(encodeURIComponent).join("/")}#L${evidence.start_line}-L${evidence.end_line}`;
}
