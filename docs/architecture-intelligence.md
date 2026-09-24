# Architecture intelligence (v0.5)

Architecture is a deterministic projection of the same commit-pinned file/import graph
used by the explorer and impact analysis. It does not infer runtime calls, API requests,
database usage or service communication. An unresolved import cannot create a violation.

## Configure a repository

Commit `.devlens.json` at the repository root before analyzing it. JSON is deliberately
used instead of executable configuration or a YAML dependency. This example declares
path ownership and dependency policies; adapt paths to the repository being analyzed.

```json
{
  "architecture": {
    "layers": {
      "frontend": ["apps/web/**"],
      "api": ["services/api/routes/**"],
      "domain": ["services/api/domain/**"],
      "data": ["services/api/storage/**", "services/api/repositories/**"]
    },
    "rules": [
      {"id": "frontend-boundary", "from": "frontend", "allow": ["frontend", "api"]},
      {"id": "api-boundary", "from": "api", "allow": ["api", "domain"]},
      {"id": "domain-boundary", "from": "domain", "deny": ["frontend", "api"]},
      {"id": "data-boundary", "from": "data", "deny": ["frontend"]}
    ]
  }
}
```

Paths are case-sensitive, repository-relative and slash-separated. `*` matches within
one segment; `**` matches zero or more complete segments. `?` and character classes use
shell-style matching within a segment. Absolute paths, backslashes, `.`/`..` segments
and empty segments are rejected. No filesystem glob expansion or code execution occurs.

Every rule needs a unique `id`, a `from` layer and exactly one of `allow` or `deny`.
All references must name declared layers. `allow` rejects resolved imports to any other
known layer; `deny` rejects only listed layers. Same-layer imports are evaluated too:
include the source layer in `allow` when internal imports are intended. An empty allow
list forbids every known target; an empty deny list forbids none. All matching rules
apply independently. There is no priority override and no invented severity score.

Unknown keys, duplicate JSON keys, invalid types and unknown layer references fail the
analysis with a configuration error. Limits: 32 layers, 32 patterns per layer, 200
characters per pattern, 128 rules, 60-character rule IDs. Configuration is read from
regular Git blobs only, with a 64 KiB per-file, 64-file and 1 MB total configuration
budget shared with `tsconfig.json`. Symlinks and vendor/generated paths remain excluded.

## Classification and uncertainty

1. One configured layer matching a path wins; multiple matching patterns in the same
   layer agree. Matches in different layers produce `unknown`, with the conflict shown.
2. Without a configured match, test file/directory naming implies the `tests` layer.
3. Recognized directory segments (`frontend`, `controllers`, `domain`, `repositories`,
   `infrastructure`, `routes`, `utils`) provide explicitly labeled convention inference.
4. Conflicting conventions or no recognized evidence produce `unknown`.

Configured names may include presentation, service, data, database or other project
concepts. DevLens does not assume that every directory called `services` is one layer.
Every assignment contains the matching paths or convention evidence and its method.
Unknown layers are excluded from rule verdicts. With no rules, zero violations means
only that no configured violation was found, not that an architecture is compliant.

## Dependencies, cycles and evidence

Every import arrow means **consumer → dependency**. Layer-map counts are numbers of
resolved import edges, including separate import statements between the same files.
Click a relationship, or use its keyboard-accessible table row, to inspect contributing
files. Dependency pages distinguish violation, unclassified and no violation detected.
They filter source/target layer, rule, language, path and relationship type.

Cycle detection uses iterative Kosaraju strongly connected components. Traversal is
linear in vertices/edges after deterministic sorting. Self-loops, two-file and longer
cycles are detected; containment edges are excluded. Each cyclic component has all its
members and one deterministic closed witness made of real import edges. This is not
enumeration of all elementary cycles. IDs are stable within identical snapshots, not
permanent identities across changed commits.

Directory cycles aggregate imports between immediate parent directories, excluding
within-directory links. A directory cycle does **not** prove a file cycle: different
files can supply each leg. Every displayed leg links to its actual source import.

Relationship evidence shows source and target side by side, line numbers, extraction
method, and links pinned to the snapshot SHA. Excerpts are at most five lines of 240
characters each per evidence location. The target is the resolved file, with its opening
lines as context; it is **not** a claim that an imported identifier binds to a particular
target declaration. Older snapshots may have no excerpts. Source excerpts are persisted
and exported: see [privacy](privacy-architecture.md).

## Views and bounds

The repository explorer retains file/symbol graph and list modes. Architecture adds a
layer map, classification evidence, dependencies, violations, cycle explorer and
categorized limitations. Layer maps render at most 100 links with the full aggregate
table available. Cycle graphs render at most 50 witness nodes; every witness edge remains
inspectable in pages of 20. Query pages default to 50 and allow at most 100 items; the
UI requests 20. A cycle detail includes its full bounded component/witness. Large
snapshot exports and cycle details can still be sizable.

Search supports `layer:domain`, `type:class`, `path:payments`, `import:@/store`,
`cycle:true` and `violation:true`; space-separated clauses are combined with AND.
Plain terms search paths and declaration names. Cycle search means file-component
membership; violation search finds both endpoints and declarations in those files.
Candidate tests use naming and reachability, never measured coverage.

Skipped files, parser failures, computed imports, unsupported resolution and configuration
limitations can hide dependencies, cycles or violations. Counts describe analyzed
evidence, not a completeness score. Invalid architecture config or exhausted resource
budgets fail explicitly. Risk scoring, history and architecture drift comparison remain
future work.

## Persistence and verification

Schema-v2 JSON snapshots store architecture assignments, rules, witnesses, violations,
metrics and evidence alongside the graph. Persisting the results preserves the analyzer
version's interpretation instead of silently recomputing old snapshots with new rules.
Existing relational tables are unchanged, so no new Alembic revision is needed.
Schema-v1 graph/export/impact reads remain supported. Architecture queries on them return
409 with a request to analyze again; stored snapshots are never rewritten automatically.

`tests/test_architecture.py`, API tests, component tests and the browser architecture
fixture verify configured valid imports, one intentional domain-to-frontend violation,
a three-file cycle, aliases, candidate tests, determinism and evidence. The fixture is
test-only and cannot substitute for a production GitHub clone.
