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
          <strong>{report.direct.length}</strong>
          <span>Direct</span>
        </div>
        <div>
          <strong>{report.indirect.length}</strong>
          <span>Transitive</span>
        </div>
        <div>
          <strong>{report.candidate_tests.length}</strong>
          <span>Candidate tests</span>
        </div>
      </div>
      {entries.length === 0 && (
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
