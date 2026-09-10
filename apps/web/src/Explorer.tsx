import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  FileCode2,
  GitBranch,
  List,
  Network,
  Search,
} from "lucide-react";
import TwinGraph from "./TwinGraph";
import ImpactPanel from "./ImpactPanel";
import {
  api,
  evidenceUrl,
  type GraphData,
  type GraphNode,
  type ImpactReport,
  type Run,
} from "./types";

export default function Explorer({
  run,
  setError,
}: {
  run: Run;
  setError: (message: string) => void;
}) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [report, setReport] = useState<ImpactReport | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactRequest, setImpactRequest] = useState<{
    target: string;
    sequence: number;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("file");
  const [language, setLanguage] = useState("");
  const [offset, setOffset] = useState(0);
  const [view, setView] = useState<"graph" | "list">("graph");
  useEffect(() => {
    if (run?.status !== "completed") {
      setGraph(null);
      return;
    }
    const controller = new AbortController();
    setGraphLoading(true);
    setGraph(null);
    const timer = setTimeout(() => {
      const query = new URLSearchParams({
        q: search,
        kind,
        language,
        offset: String(offset),
        limit: "100",
      });
      void api<GraphData>(`/analysis/${run.id}/graph?${query}`, {
        signal: controller.signal,
      })
        .then((data) => {
          setGraph(data);
          setGraphLoading(false);
        })
        .catch((e) => {
          if (e.name !== "AbortError") {
            setError(e.message);
            setGraphLoading(false);
          }
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [run?.id, run?.status, search, kind, language, offset, setError]);

  useEffect(() => {
    setSelected(null);
    setReport(null);
    setImpactRequest(null);
    setOffset(0);
  }, [run?.id]);

  useEffect(() => {
    setReport(null);
    if (!impactRequest || !run?.id) {
      setImpactLoading(false);
      return;
    }
    setImpactLoading(true);
    const controller = new AbortController();
    void api<ImpactReport>(
      `/analysis/${run.id}/impact?target=${encodeURIComponent(impactRequest.target)}`,
      { signal: controller.signal },
    )
      .then((data) => {
        setReport(data);
        setImpactLoading(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setImpactLoading(false);
        }
      });
    return () => controller.abort();
  }, [run?.id, impactRequest, setError]);

  const affected = useMemo(
    () =>
      new Set(
        report
          ? [
              report.target.id,
              `file:${report.target.path}`,
              ...report.direct.map((x) => x.node.id),
              ...report.indirect.map((x) => x.node.id),
            ]
          : [],
      ),
    [report],
  );

  function choose(node: GraphNode) {
    setSelected(node);
    setReport(null);
    setImpactLoading(false);
    setImpactRequest(null);
  }

  if (!run.summary) return null;
  return (
    <>
      <section className="explorer" aria-label="Digital twin explorer">
        <div className="explorer-heading">
          <div>
            <Network size={18} />
            <h2>Repository digital twin</h2>
          </div>
          <span className="muted">
            Arrows point from consumer to dependency
          </span>
        </div>
        <div className="toolbar">
          <label className="search">
            <Search size={15} />
            <input
              aria-label="Search graph"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setOffset(0);
              }}
              placeholder="Search files or symbols…"
            />
          </label>
          <select
            aria-label="Node type"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All nodes</option>
            <option value="file">Files</option>
            <option value="function">Functions</option>
            <option value="class">Classes</option>
            <option value="method">Methods</option>
            <option value="interface">Interfaces</option>
          </select>
          <select
            aria-label="Language"
            value={language}
            onChange={(e) => {
              setLanguage(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All languages</option>
            {Object.keys(run.summary.languages).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <div className="view-toggle">
            <button
              aria-label="Graph view"
              aria-pressed={view === "graph"}
              onClick={() => setView("graph")}
            >
              <Network size={16} />
            </button>
            <button
              aria-label="List view"
              aria-pressed={view === "list"}
              onClick={() => setView("list")}
            >
              <List size={16} />
            </button>
          </div>
        </div>
        <div className="explorer-body">
          <div className="graph-area">
            {graphLoading ? (
              <div className="graph-empty" role="status">
                Loading repository graph…
              </div>
            ) : graph && graph.nodes.length > 0 ? (
              view === "graph" ? (
                <TwinGraph
                  graph={graph}
                  selected={selected?.id ?? null}
                  affected={affected}
                  onSelect={choose}
                />
              ) : (
                <div className="node-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Source / declaration</th>
                        <th>Kind</th>
                        <th>Language</th>
                      </tr>
                    </thead>
                    <tbody>
                      {graph.nodes.map((node) => (
                        <tr
                          key={node.id}
                          data-selected={selected?.id === node.id}
                        >
                          <td>
                            <button onClick={() => choose(node)}>
                              {node.label}
                            </button>
                            <small>
                              {node.kind !== "file" ? node.path : ""}
                            </small>
                          </td>
                          <td>{node.kind}</td>
                          <td>{node.language}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              <div className="graph-empty">
                <Search size={25} />
                <p>
                  {run.summary.source_file_count === 0
                    ? "No supported source files found in this snapshot."
                    : "No nodes match these filters."}
                </p>
              </div>
            )}
            <div className="graph-footer">
              <span>
                {graph
                  ? `${graph.offset + (graph.nodes.length ? 1 : 0)}–${graph.offset + graph.nodes.length} of ${graph.total} nodes`
                  : "Loading…"}{" "}
                · edges within this page
              </span>
              <div>
                <button
                  aria-label="Previous graph page"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 100))}
                >
                  <ChevronLeft size={15} />
                </button>
                <button
                  aria-label="Next graph page"
                  disabled={!graph?.truncated}
                  onClick={() => setOffset(offset + 100)}
                >
                  <ChevronRight size={15} />
                </button>
              </div>
            </div>
          </div>
          <aside className="detail-panel" aria-label="Node details">
            {selected ? (
              <>
                <p className="eyebrow">{selected.kind} DETAILS</p>
                <h3>{selected.label}</h3>
                <p className="node-path">{selected.path}</p>
                <div className="detail-tags">
                  <span className="pill">{selected.language}</span>
                  <span className="pill">
                    Lines {selected.evidence.start_line}–
                    {selected.evidence.end_line}
                  </span>
                </div>
                <p className="muted">
                  Observed with {selected.evidence.method}.
                </p>
                <a
                  className="evidence-link"
                  href={evidenceUrl(run, selected.evidence)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Inspect source evidence <ArrowUpRight size={14} />
                </a>
                <button
                  className="primary impact-button"
                  disabled={impactLoading}
                  onClick={() =>
                    setImpactRequest({
                      target: selected.id,
                      sequence: Date.now(),
                    })
                  }
                >
                  <GitBranch size={16} />
                  {impactLoading
                    ? "Tracing imports…"
                    : "Simulate change impact"}
                </button>
                {report && <ImpactPanel report={report} run={run} />}
              </>
            ) : (
              <div className="selection-empty">
                <div>
                  <FileCode2 size={25} />
                </div>
                <h3>Follow a dependency.</h3>
                <p>
                  Select a node to inspect its evidence and trace potential
                  change impact.
                </p>
                <small>
                  Prefer a table? Switch to list view for full keyboard
                  navigation.
                </small>
              </div>
            )}
          </aside>
        </div>
      </section>
      <details className="limitations">
        <summary>
          Analysis coverage & limitations{" "}
          <span>{graph?.limitations.length ?? "…"} observations</span>
        </summary>
        <p>
          Skipped entries:{" "}
          {Object.entries(run.summary.skipped)
            .map(([key, value]) => `${value} ${key.replaceAll("_", " ")}`)
            .join(" · ") || "None"}
          . CommonJS, path aliases, runtime calls and external-package internals
          are not resolved.
        </p>
        {graph?.limitations.map((item, index) => (
          <div className="limitation" key={`${item.path}:${index}`}>
            <code>
              {item.path}:{item.line}
            </code>
            <span>
              {item.reason}
              {item.specifier ? ` (${item.specifier})` : ""}
            </span>
          </div>
        ))}
      </details>
    </>
  );
}
