import { ExternalLink, GitBranch } from "lucide-react";
import { evidenceUrl, type ImpactReport, type Run } from "./types";

export default function ImpactPanel({
  report,
  run,
}: {
  report: ImpactReport;
  run: Run;
}) {
  const entries = [...report.direct, ...report.indirect];
  return (
    <section className="impact-panel" aria-label="Impact results">
      <div className="section-title">
        <GitBranch size={18} />
        <h3>Potential change surface</h3>
      </div>
      <p className="muted">Scope: {report.scope}</p>
      <div className="impact-counts">
        <div>
          <strong>{report.direct_count ?? report.direct.length}</strong>
          <span>Direct</span>
        </div>
        <div>
          <strong>{report.indirect_count ?? report.indirect.length}</strong>
          <span>Transitive</span>
        </div>
        <div>
          <strong>{report.candidate_tests.length}</strong>
          <span>Candidate tests</span>
        </div>
      </div>
      {report.affected_layers && (
        <div className="impact-context">
          <p>
            <strong>Affected layers:</strong>{" "}
            {report.affected_layers.join(", ") || "None classified"}
          </p>
          <p>
            <strong>Involved cycle groups:</strong>{" "}
            {report.affected_cycles?.join(", ") || "None"}
          </p>
          <p>
            <strong>Related violations:</strong>{" "}
            {report.affected_violations?.length ?? 0}
          </p>
          <p>
            <strong>Related rule IDs:</strong>{" "}
            {report.affected_rules?.join(", ") || "None"}
          </p>
          <p>
            These are existing relationships touched by the potential change
            surface, not predicted new violations.
          </p>
          <details>
            <summary>
              Candidate test paths ({report.candidate_tests.length})
            </summary>
            <ul>
              {report.candidate_tests.map((path) => (
                <li key={path}>{path}</li>
              ))}
            </ul>
          </details>
          <details>
            <summary>
              Outgoing direct dependencies (
              {report.outgoing_dependencies?.length ?? 0})
            </summary>
            <ul>
              {report.outgoing_dependencies?.map((path) => (
                <li key={path}>{path}</li>
              ))}
            </ul>
          </details>
          <p>
            Incoming dependents below ·{" "}
            {entries.length ? (report.offset ?? 0) + 1 : 0}–
            {(report.offset ?? 0) + entries.length} of{" "}
            {report.total ?? entries.length}
          </p>
        </div>
      )}
      {(report.total ?? entries.length) === 0 && (
        <p>
          No import-reachable consumers were found within the analyzed files.
          This does not prove the change is safe.
        </p>
      )}
      {entries.map((entry) => (
        <details key={entry.node.id} className="impact-entry">
          <summary>
            <span>{entry.node.path}</span>
            <small>
              {entry.distance === 1 ? "Direct" : `${entry.distance} hops`}
            </small>
          </summary>
          <p className="eyebrow">{entry.classification}</p>
          {entry.path_truncated && (
            <p>
              Evidence path truncated by the response budget. Export the
              snapshot to inspect the full graph.
            </p>
          )}
          <ol>
            {entry.evidence_path.map((edge) => (
              <li key={edge.id}>
                <span>
                  {edge.source.replace("file:", "")} →{" "}
                  {edge.target.replace("file:", "")}
                </span>
                <a
                  href={evidenceUrl(run, edge.evidence)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Line {edge.evidence.start_line} <ExternalLink size={12} />
                </a>
              </li>
            ))}
          </ol>
        </details>
      ))}
      <details className="methodology" open>
        <summary>Interpretation & limitations</summary>
        <ul>
          {report.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
