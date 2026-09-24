# Architecture

DevLens is a modular monolith: React/Vite → FastAPI → analysis modules → PostgreSQL.
The API schedules one bounded in-process analysis at a time. Persisted run states
survive restarts; interrupted runs become failed rather than silently hanging.
Run exactly one API worker. A durable queue is a later scaling decision.

## Modules

- `apps/web`: React/TypeScript UI; React Flow provides keyboard-accessible graph controls.
- `services/api/src/devlens/ingestion.py`: URL validation, isolated Git, resource limits.
- `parsers.py`: AST declarations and literal imports; no repository execution.
- `analysis.py`: deterministic graph construction, resolution, evidence and metrics.
- `resolution.py`: conservative path/package resolution and data-only tsconfig support.
- `architecture_rules.py`, `architecture.py`, `cycles.py`: strict rule data, explainable layers,
  observed violations, deterministic strongly connected components and closed witnesses.
- `queries.py`, `architecture_api.py`: typed search and paginated architecture/dependency views.
- `impact.py`: reverse breadth-first traversal with evidence paths.
- `storage.py` and `migrations`: SQLAlchemy persistence and Alembic schema versioning.
- `main.py`: request validation, lifecycle, admission control and versioned REST API.

Analyzer modules stay inside the Python package until a useful plugin boundary stabilizes.
Empty SDK packages and additional backend services are deliberately deferred.

## Evidence model

Snapshot → commit SHA + analyzer version + files + declarations + typed edges.
Each declaration and import has repository-relative path, start/end line and extraction
method. `imports` points from consumer to dependency. `contains` is structural and is
never traversed as a dependency. Reverse import reachability supplies impact paths.
IDs derive deterministically from path and declaration position, not random values.

## Data and lifecycle

An analysis row stores URL, state, stage, timestamps, sanitized error and a versioned
JSON graph document. PostgreSQL is the reference database; SQLite supports isolated
unit tests and an explicit lightweight local mode. Alembic owns schema creation.
Repository temporary storage is removed after extraction. Schema-v2 snapshots persist bounded source excerpts (five lines, 240 characters per line
per evidence location), architecture results and factual counts; full files are not retained.
Schema-v1 remains readable and is never automatically rewritten. Architecture requests
for legacy data require reanalysis. No relational schema change is needed.
Delete removes the row, graph and excerpts. Graph API pages nodes and reports truncation.

## Security boundary

Only public github.com HTTPS remotes; no credentials, ports, query, fragments or redirects.
Git receives argument arrays, an isolated environment/config, no hooks, no submodules,
no checkout, no LFS smudge and no prompting. Reads use Git object IDs. Symlinks,
submodules, binaries, generated directories and oversized files are skipped. Clone time,
disk usage, tree entries, source bytes and source file counts are bounded. The container
runs as a non-root user with memory/CPU limits. Do not expose this unauthenticated MVP
to a public network. See SECURITY.md and docs/privacy-architecture.md.

## Performance and boundaries

Each file is parsed once per run. Resolver inputs and source lines are reused. Iterative
SCC traversal and indexed breadth-first impact traversal avoid recursive graph walks;
impact paths are materialized only for the requested page with explicit response budgets.
Architecture visuals are bounded and have table alternatives. Snapshot JSON is still
loaded and validated per request; recent-run listing also reads complete snapshot rows.
Storage projection/caching and hard worker isolation remain scaling priorities.
See [architecture methodology](docs/architecture-intelligence.md) for classification,
rule semantics and witness limitations.
