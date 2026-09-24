# REST API v1

Interactive OpenAPI: `http://localhost:8000/docs` when the local API is running.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/health` | Database connectivity and application version |
| POST | `/api/v1/analysis` | `{ "repository_url": "https://github.com/owner/repo" }`; 202 with run ID |
| GET | `/api/v1/analysis` | Most recent 50 analysis runs |
| GET | `/api/v1/analysis/{id}` | Status, stage, safe error and snapshot summary |
| GET | `/api/v1/analysis/{id}/graph` | `q`, `kind`, `language`, `offset`, `limit` (1–500) |
| GET | `/api/v1/analysis/{id}/impact?target={node_id}` | Incoming direct/transitive consumers, architecture context; `offset`, `limit` (1–100) |
| GET | `/api/v1/analysis/{id}/architecture` | SHA, configuration, file counts by layer, observed directed aggregates, rules, factual metrics |
| GET | `/api/v1/analysis/{id}/architecture/layers` | Classification evidence; `layer`, `path` |
| GET | `/api/v1/analysis/{id}/relationships` | Resolved imports with endpoint evidence; `source_layer`, `target_layer`, `rule`, `language`, `path`, `status` |
| GET | `/api/v1/analysis/{id}/architecture/violations` | Same filters, always restricted to imports with configured violations |
| GET | `/api/v1/analysis/{id}/cycles` | Cyclic components; `kind=file` or `directory`, `path` |
| GET | `/api/v1/analysis/{id}/cycles/{cycle_id}` | Complete component, closed witness and each witness edge's evidence |
| GET | `/api/v1/analysis/{id}/dependencies` | `target`, `direction=incoming/outgoing`, `depth=direct/transitive`; paginated reachable import edges |
| GET | `/api/v1/analysis/{id}/limitations` | Categorized extraction limitations; `category` |
| GET | `/api/v1/analysis/{id}/snapshot` | Complete bounded versioned JSON export (new analyses use schema v2) |
| DELETE | `/api/v1/analysis/{id}` | Delete finished/failed analysis; 204 |

States: queued → running → completed or failed. Stages: fetching, reading, parsing,
completed; failures record their stage. Poll at roughly one-second intervals. There is
one active job per process; excess POSTs receive 429 + Retry-After. Do not run multiple
API workers. Restarted in-flight jobs become failed and require resubmission.

Missing run/target: 404. Invalid URL/query: 422. Incomplete graph or deletion of a running
job: 409. Architecture on legacy snapshots: 409 with reanalysis guidance. Invalid Host: 400.
Browser cross-origin requests: 403. This local API is unauthenticated and must
not be exposed publicly. Error responses never include Git stderr or source content.

Architecture layers, relationships, violations, cycle lists, dependencies and limitations
use `{items, total, offset, limit, truncated, commit_sha}`. Defaults are offset 0 and
limit 50 (maximum 100). Ordering is deterministic for an unchanged snapshot. `status`
accepts `violation`, `unclassified`, or `no violation detected`; an empty filter matches
all. A no-violation label is not proof of architectural compliance. Rule objects expose
`id`, `from`, and exactly one non-null `allow`/`deny` list.

Graph `q` supports name/path terms and AND-combined `layer:`, `type:`, `path:`, `import:`,
`cycle:true/false`, `violation:true/false` clauses. `type:test` filters test file nodes;
`type:file` includes test files. Bad clauses return 422. Returned graph edges have both
endpoints on the page. Graph responses include only the first 100 limitations plus
`limitations_total`; use the limitations endpoint for the rest.

Dependency arrows always retain consumer → dependency meaning, including incoming
queries. Transitive dependency queries return edges reached during traversal, including
cycle-closing edges; they do not invent transitive direct edges. Symbol targets use their
containing file. Impact full counts/context are independent of paging; evidence paths
have explicit truncation flags and budgets described in [change impact](change-impact.md).

New snapshots store bounded excerpts in `evidence.snippet: [{number, text}]` and add
`architecture`, `metrics` and optional edge `specifier`. Schema-v1 fields remain accepted;
missing excerpts/architecture are not fabricated. Normal evidence responses and exports
contain source excerpts intentionally; error messages do not. No automatic snapshot or
relational database migration is required for this additive JSON version.
