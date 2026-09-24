import { useEffect, useState } from "react";
import { api, type Run, type Limitation } from "./types";
import type {
  ArchitectureSummary,
  Assignment,
  Cycle,
  CycleDetail,
  LayerLink,
  Page,
  Relationship,
} from "./architecture-types";
import ArchitectureMap, { CycleMap } from "./ArchitectureMap";
import EvidencePanel from "./EvidencePanel";

type View =
  "map" | "layers" | "relationships" | "violations" | "cycles" | "limitations";
type Item = Assignment | Relationship | Cycle | Limitation;
const labels: Record<View, string> = {
  map: "Architecture map",
  layers: "Layer evidence",
  relationships: "Dependencies",
  violations: "Violations",
  cycles: "Cycles",
  limitations: "Limitations",
};

export default function Architecture({ run }: { run: Run }) {
  const [summary, setSummary] = useState<ArchitectureSummary | null>(null);
  const [view, setView] = useState<View>("map");
  const [data, setData] = useState<Page<Item> | null>(null);
  const [error, setError] = useState("");
  const [path, setPath] = useState("");
  const [layer, setLayer] = useState("");
  const [targetLayer, setTargetLayer] = useState("");
  const [rule, setRule] = useState("");
  const [language, setLanguage] = useState("");
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Relationship | null>(null);
  const [cycleId, setCycleId] = useState("");
  const [cycle, setCycle] = useState<CycleDetail | null>(null);
  const [cycleOffset, setCycleOffset] = useState(0);
  const prefix = `/analysis/${run.id}`;

  useEffect(() => {
    const controller = new AbortController();
    void api<ArchitectureSummary>(`${prefix}/architecture`, {
      signal: controller.signal,
    })
      .then(setSummary)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [prefix]);
  useEffect(() => {
    if (view === "map") return;
    const controller = new AbortController();
    setData(null);
    setError("");
    setSelected(null);
    const query = new URLSearchParams({
      path,
      source_layer: layer,
      layer,
      target_layer: targetLayer,
      rule,
      language,
      kind,
      category,
      status,
      offset: String(offset),
      limit: "20",
    });
    const route =
      view === "layers" || view === "violations"
        ? `architecture/${view}`
        : view;
    const timer = setTimeout(() => {
      void api<Page<Item>>(`${prefix}/${route}?${query}`, {
        signal: controller.signal,
      })
        .then(setData)
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [
    prefix,
    view,
    path,
    layer,
    targetLayer,
    rule,
    language,
    kind,
    category,
    status,
    offset,
  ]);
  useEffect(() => {
    setCycle(null);
    setCycleOffset(0);
    if (!cycleId) return;
    const controller = new AbortController();
    void api<CycleDetail>(`${prefix}/cycles/${encodeURIComponent(cycleId)}`, {
      signal: controller.signal,
    })
      .then(setCycle)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [prefix, cycleId]);
  function navigate(next: View) {
    setView(next);
    setOffset(0);
    setSelected(null);
    setCycleId("");
    setLayer("");
    setTargetLayer("");
    setRule("");
    setPath("");
    setLanguage("");
    setKind("");
    setStatus("");
    setCategory("");
    setError("");
  }
  function relationship(link: LayerLink) {
    navigate("relationships");
    setLayer(link.source);
    setTargetLayer(link.target);
  }
  const filtering = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setOffset(0);
    setCycleId("");
  };
  return (
    <section
      className="architecture-section"
      aria-label="Architecture intelligence"
    >
      <div className="section-title">
        <h2>Architecture intelligence</h2>
        <span className="pill">Commit-pinned evidence</span>
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {!summary && !error && <p role="status">Loading architecture…</p>}
      {summary && (
        <>
          <p className="muted">
            {summary.configuration
              ? `Configured with ${summary.configuration}`
              : "No explicit rules. Recognized directory conventions are labeled as inference; other files remain unknown."}
          </p>
          {summary.rules.length > 0 && (
            <details className="configured-rules">
              <summary>Configured rules ({summary.rules.length})</summary>
              <ul>
                {summary.rules.map((item) => (
                  <li key={item.id}>
                    <strong>{item.id}</strong>: {item.from} →{" "}
                    {item.allow
                      ? `allow only ${item.allow.join(", ")}`
                      : `deny ${item.deny?.join(", ")}`}
                  </li>
                ))}
              </ul>
              <p>
                All matching rules apply, including within-layer imports.
                Unknown layers are not evaluated.
              </p>
            </details>
          )}
          <div className="analysis-facts" aria-label="Analysis facts">
            {Object.entries({
              Files: run.summary?.source_file_count ?? 0,
              Declarations: summary.metrics.declarations ?? 0,
              "Resolved import edges":
                summary.metrics.resolved_import_edges ?? 0,
              "Unresolved imports": summary.metrics.unresolved_imports ?? 0,
              Layers: summary.metrics.layers ?? 0,
              Violations: summary.metrics.violations ?? 0,
              "File cycle groups": summary.metrics.file_cycle_groups ?? 0,
              "Directory cycle groups":
                summary.metrics.directory_cycle_groups ?? 0,
              "Candidate test files": summary.metrics.candidate_test_files ?? 0,
              "Parse errors": summary.metrics.parse_errors ?? 0,
            }).map(([name, count]) => (
              <div key={name}>
                <strong>{count}</strong>
                <span>{name}</span>
              </div>
            ))}
          </div>
          <nav className="section-tabs" aria-label="Architecture views">
            {(Object.keys(labels) as View[]).map((key) => (
              <button
                key={key}
                aria-pressed={view === key}
                onClick={() => navigate(key)}
              >
                {labels[key]}
              </button>
            ))}
          </nav>
          {view === "map" ? (
            <>
              {Object.keys(summary.layers).length ? (
                <ArchitectureMap
                  summary={summary}
                  onRelationship={relationship}
                />
              ) : (
                <p>No supported source files to classify.</p>
              )}
              <div className="audit-table">
                <table>
                  <caption>
                    Observed layer dependencies: consumer → dependency
                  </caption>
                  <thead>
                    <tr>
                      <th>Consumer layer</th>
                      <th>Dependency layer</th>
                      <th>Import edges</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.relationships.map((link) => (
                      <tr key={`${link.source}:${link.target}`}>
                        <td>{link.source}</td>
                        <td>{link.target}</td>
                        <td>{link.count}</td>
                        <td>
                          <button onClick={() => relationship(link)}>
                            Inspect {link.source} → {link.target}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!summary.relationships.length && (
                <p>
                  No resolved import relationships were found. This does not
                  establish architectural independence.
                </p>
              )}
            </>
          ) : (
            <>
              <div className="audit-filters">
                {view !== "limitations" && (
                  <label>
                    Path
                    <input
                      value={path}
                      onChange={(e) => filtering(setPath)(e.target.value)}
                    />
                  </label>
                )}
                {!["cycles", "limitations"].includes(view) && (
                  <label>
                    {view === "layers" ? "Layer" : "Source layer"}
                    <select
                      aria-label={view === "layers" ? "Layer" : "Source layer"}
                      value={layer}
                      onChange={(e) => filtering(setLayer)(e.target.value)}
                    >
                      <option value="">All layers</option>
                      {Object.keys(summary.layers).map((name) => (
                        <option key={name}>{name}</option>
                      ))}
                    </select>
                  </label>
                )}
                {["relationships", "violations"].includes(view) && (
                  <>
                    <label>
                      Target layer
                      <select
                        aria-label="Target layer"
                        value={targetLayer}
                        onChange={(e) =>
                          filtering(setTargetLayer)(e.target.value)
                        }
                      >
                        <option value="">All layers</option>
                        {Object.keys(summary.layers).map((name) => (
                          <option key={name}>{name}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Rule
                      <select
                        aria-label="Rule"
                        value={rule}
                        onChange={(e) => filtering(setRule)(e.target.value)}
                      >
                        <option value="">All rules</option>
                        {summary.rules.map((r) => (
                          <option key={r.id}>{r.id}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Language
                      <select
                        aria-label="Language"
                        value={language}
                        onChange={(e) => filtering(setLanguage)(e.target.value)}
                      >
                        <option value="">All languages</option>
                        {Object.keys(run.summary?.languages ?? {}).map(
                          (name) => (
                            <option key={name}>{name}</option>
                          ),
                        )}
                      </select>
                    </label>
                  </>
                )}
                {view === "relationships" && (
                  <label>
                    Relationship type
                    <select
                      aria-label="Relationship type"
                      value={status}
                      onChange={(e) => filtering(setStatus)(e.target.value)}
                    >
                      <option value="">All types</option>
                      <option value="violation">Violation</option>
                      <option value="unclassified">Unclassified</option>
                      <option value="no violation detected">
                        No violation detected
                      </option>
                    </select>
                  </label>
                )}
                {view === "cycles" && (
                  <label>
                    Cycle type
                    <select
                      aria-label="Cycle type"
                      value={kind}
                      onChange={(e) => filtering(setKind)(e.target.value)}
                    >
                      <option value="">All cycles</option>
                      <option value="file">File</option>
                      <option value="directory">Directory</option>
                    </select>
                  </label>
                )}
                {view === "limitations" && (
                  <label>
                    Limitation category
                    <select
                      aria-label="Limitation category"
                      value={category}
                      onChange={(e) => filtering(setCategory)(e.target.value)}
                    >
                      <option value="">All categories</option>
                      {[
                        "unresolved_import",
                        "dynamic_import",
                        "parse_error",
                        "configuration",
                      ].map((value) => (
                        <option key={value}>{value}</option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              {view === "limitations" && (
                <div className="notice">
                  <div>
                    <p>
                      Skipped entries:{" "}
                      {Object.entries(run.summary?.skipped ?? {})
                        .map(
                          ([name, count]) =>
                            `${name.replaceAll("_", " ")}: ${count}`,
                        )
                        .join(" · ") || "None"}
                      .
                    </p>
                    <p>
                      Skipped files, dynamic imports and parse errors can hide
                      consumers, cycles and violations. Budget exhaustion fails
                      the analysis explicitly; no incomplete success is
                      fabricated.
                    </p>
                  </div>
                </div>
              )}
              {!data && !error && (
                <p role="status">Loading {labels[view].toLowerCase()}…</p>
              )}
              {data && (
                <>
                  {!data.items.length && (
                    <p className="notice">
                      No {labels[view].toLowerCase()} match these filters.
                      {view === "violations" && !summary.rules.length
                        ? " No architecture rules are configured; absence of violations is not a compliance verdict."
                        : ""}
                    </p>
                  )}
                  {view === "layers" && (
                    <div className="audit-table">
                      <table>
                        <caption>Classification evidence</caption>
                        <thead>
                          <tr>
                            <th>File</th>
                            <th>Layer</th>
                            <th>How determined</th>
                            <th>Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(data.items as Assignment[]).map((item) => (
                            <tr key={item.node_id}>
                              <td>{item.path}</td>
                              <td>{item.layer}</td>
                              <td>{item.method}</td>
                              <td>{item.evidence.join("; ")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {["relationships", "violations"].includes(view) && (
                    <div className="audit-table">
                      <table>
                        <caption>
                          Import evidence: consumer → dependency
                        </caption>
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Source / layer</th>
                            <th>Target / layer</th>
                            <th>Rule</th>
                            <th>Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(data.items as Relationship[]).map((item) => (
                            <tr key={item.edge.id}>
                              <td>{item.status}</td>
                              <td>
                                {item.source.path}
                                <small>{item.source_layer}</small>
                              </td>
                              <td>
                                {item.target.path}
                                <small>{item.target_layer}</small>
                              </td>
                              <td>{item.rule_ids.join(", ") || "—"}</td>
                              <td>
                                <button onClick={() => setSelected(item)}>
                                  Inspect line {item.edge.evidence.start_line}
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {view === "cycles" && (
                    <>
                      <p>
                        One closed witness per strongly connected component.
                        Directory cycles aggregate real imports and do not prove
                        a file-level cycle.
                      </p>
                      <ul className="cycle-list">
                        {(data.items as Cycle[]).map((item) => (
                          <li key={item.id}>
                            <button onClick={() => setCycleId(item.id)}>
                              {item.id} · {item.members.length} members
                            </button>
                            <p>
                              {item.path
                                .slice(0, 6)
                                .map((p) => p.replace(/^file:/, ""))
                                .join(" → ")}
                              {item.path.length > 6 ? " …" : ""}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {view === "limitations" && (
                    <ul className="limitation-list">
                      {(data.items as Limitation[]).map((item, index) => (
                        <li key={index}>
                          <strong>{item.category?.replaceAll("_", " ")}</strong>
                          <code>
                            {item.path}:{item.line}
                          </code>
                          <p>
                            {item.reason} {item.specifier}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="audit-pagination">
                    <span>
                      {data.total} results ·{" "}
                      {data.items.length ? data.offset + 1 : 0}–
                      {data.offset + data.items.length}
                    </span>
                    <button
                      disabled={!offset}
                      onClick={() => setOffset(Math.max(0, offset - 20))}
                    >
                      Previous results
                    </button>
                    <button
                      disabled={!data.truncated}
                      onClick={() => setOffset(offset + 20)}
                    >
                      Next results
                    </button>
                  </div>
                </>
              )}
            </>
          )}
          {cycleId && !cycle && !error && (
            <p role="status">Loading cycle evidence…</p>
          )}
          {cycle && view === "cycles" && (
            <section aria-label="Selected cycle">
              <h3>{cycle.cycle.id}</h3>
              <CycleMap detail={cycle} />
              <p>
                First 50 witness nodes rendered. All{" "}
                {cycle.cycle.members.length} component members are listed below;
                the witness may visit a subset.
              </p>
              <details>
                <summary>Involved files / directories</summary>
                <ul>
                  {cycle.cycle.members.map((member) => (
                    <li key={member}>{member.replace(/^file:/, "")}</li>
                  ))}
                </ul>
              </details>
              <ol start={cycleOffset + 1}>
                {cycle.relationships
                  .slice(cycleOffset, cycleOffset + 20)
                  .map((item) => (
                    <li key={item.edge.id}>
                      <button onClick={() => setSelected(item)}>
                        {item.source.path} → {item.target.path} · line{" "}
                        {item.edge.evidence.start_line}
                      </button>
                    </li>
                  ))}
              </ol>
              <div className="audit-pagination">
                <button
                  disabled={!cycleOffset}
                  onClick={() => setCycleOffset(Math.max(0, cycleOffset - 20))}
                >
                  Previous cycle edges
                </button>
                <button
                  disabled={cycleOffset + 20 >= cycle.relationships.length}
                  onClick={() => setCycleOffset(cycleOffset + 20)}
                >
                  Next cycle edges
                </button>
              </div>
            </section>
          )}
          {selected && <EvidencePanel relationship={selected} run={run} />}
        </>
      )}
    </section>
  );
}
