import { evidenceUrl, type Evidence, type Run } from "./types";
import type { Relationship } from "./architecture-types";

function Source({
  title,
  evidence,
  run,
}: {
  title: string;
  evidence: Evidence;
  run: Run;
}) {
  return (
    <section className="source-card" aria-label={title}>
      <h4>{title}</h4>
      <p className="node-path">{evidence.path}</p>
      <pre aria-label={`${title} source excerpt`}>
        {evidence.snippet?.length
          ? evidence.snippet.map((line) => (
              <span className="source-line" key={line.number}>
                <span className="line-number">{line.number}</span>
                <code>{line.text}</code>
              </span>
            ))
          : "No stored excerpt in this snapshot. Open commit-pinned source."}
      </pre>
      <a
        className="evidence-link"
        href={evidenceUrl(run, evidence)}
        target="_blank"
        rel="noreferrer"
      >
        Open source at lines {evidence.start_line}–{evidence.end_line}
      </a>
    </section>
  );
}

export default function EvidencePanel({
  relationship,
  run,
}: {
  relationship: Relationship;
  run: Run;
}) {
  return (
    <section className="evidence-panel" aria-label="Relationship evidence">
      <h3>
        {relationship.source.path} → {relationship.target.path}
      </h3>
      <p>
        Consumer → dependency · {relationship.edge.kind} ·{" "}
        {relationship.edge.evidence.method}
      </p>
      <p>
        Commit <code>{run.summary?.commit_sha}</code>
      </p>
      <p>
        {relationship.status} {relationship.rule_ids.join(", ")}
      </p>
      <div className="source-pair">
        <Source
          title="Source import"
          evidence={relationship.edge.evidence}
          run={run}
        />
        <Source
          title="Target file"
          evidence={relationship.target.evidence}
          run={run}
        />
      </div>
      <p className="muted">
        Excerpts contain at most five lines, clipped to 240 characters per line.
        Target evidence identifies the file; this is not symbol binding.
      </p>
    </section>
  );
}
