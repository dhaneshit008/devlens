# DevLens v0.5 engineering report

## 1. Repository state inspected

Continued the existing `dhaneshit008/devlens` repository after PR #1 merged into `main`.
Fetched and fast-forward synchronized main at `52de5f4aeee6f641f28f876e74d8fe97900b87d9`,
then created `feat/devlens-v0.5-architecture`. Existing commits and the Apache-2.0 license
are preserved. No main rewrite, release tag, merge or public deployment is part of this phase.
Native Git/GitHub CLI authentication was verified as `dhaneshit008` on 2026-09-24.

## 2. Main architectural decisions

Keep the FastAPI modular monolith and React explorer. Architecture is a deterministic
projection of observed file imports, stored in the same immutable commit-pinned snapshot.
Use strict `.devlens.json` data instead of executable configuration or a YAML dependency.
Keep unknown classification explicit. Preserve consumer → dependency direction everywhere.
Store bounded excerpts to make evidence inspectable without fetching live source.

## 3. Files added

Backend modules under `services/api/src/devlens`: `architecture.py`, `architecture_rules.py`,
`architecture_models.py`, `cycles.py`, `resolution.py`, `queries.py`, `architecture_api.py`.
Frontend under `apps/web/src`: `Architecture.tsx`, `ArchitectureMap.tsx`, `EvidencePanel.tsx`,
`architecture-types.ts`, `Architecture.test.tsx`, `App.test.tsx`.
Also `tests/test_architecture.py`, `apps/web/e2e/architecture.spec.ts`, `MANIFEST.in`,
`docs/architecture-intelligence.md` and two real architecture-fixture screenshots.

## 4. Files modified

Backend: analysis, parsers, ingestion, models, impact, config, main and package version.
Frontend: App, Explorer, TwinGraph, ImpactPanel, types, styles and workspace versions/lockfile.
Tests: fixtures, test API, browser fixture server and original explorer browser assertions.
Operations: CI check display names and feature-branch CodeQL trigger. Packaging manifest
now includes backend migration and test support files in the source distribution.
Documentation: README, ARCHITECTURE, PROJECT_SPEC, ROADMAP, CHANGELOG, SECURITY, this report,
and analysis-engine, change-impact, digital-twin, privacy-architecture and API docs.

## 5. Backend improvements

Typed paginated architecture, relationship, violation, dependency, cycle and limitation
queries; small AND-based search syntax; reused parse results and source lines; indexed
impact traversal and page-only path materialization. Impact full counts remain independent
of paging, with affected layers, cycles, related rule IDs and outgoing dependency paths.
Source evidence is capped at five lines of 240 characters per location. Impact paths are
capped at 200 hops and 4,000 evidence edges per response, with explicit truncation flags.

## 6. Frontend improvements

Architecture section with factual summary, directed layer map and table, rule definitions,
classification evidence, filtered dependencies/violations, cycle explorer, source evidence
and categorized limitations. All findings have table/list alternatives. Mobile history is
selectable, graph nodes open through keyboard activation, failed runs can be deleted, and
delete confirmation is tied to the selected run. Existing themes/explorer/export remain.
Dark fixture screenshots were visually inspected; browser tests cover mobile overflow.

## 7. Architecture engine implementation

Explicit path matches take precedence over test naming and conservative directory
conventions. Conflicts stay unknown. Layer maps aggregate actual resolved import edges.
No runtime calls, API/data relationships, architectural confidence or health scores are
fabricated. Full classification evidence and unresolved limitations remain inspectable.

## 8. Cycle detection implementation

Iterative Kosaraju strongly connected components, with deterministic sorting and one real
closed witness per cyclic component. Handles self-loops, two-node and multi-file cycles,
including a 1,500-node test without recursive graph walking. Directory SCCs aggregate
immediate parent directories; they are clearly distinguished from proof of file cycles.
Containment edges never participate. Every witness edge points to source evidence.

## 9. Rule engine implementation

Strict bounded JSON layers and uniquely identified allow/deny rules. Unknown keys,
duplicate keys, invalid paths, unknown layer references and conflicting policy shapes
are rejected with field-specific errors. All applicable rules are evaluated on resolved
imports, including within-layer imports. Unknown endpoints do not create verdicts.
No rules means no compliance verdict. See architecture-intelligence.md for full semantics.

## 10. Import-resolution improvements

Conservative unshadowed literal CommonJS and TypeScript import-equals extraction.
Safe nearest tsconfig JSONC aliases/baseUrl, bounded targets and explicit limitations
for unsupported inheritance/project references. Ambiguous candidates and fallback aliases
remain unresolved. Python rejects out-of-package relative imports, supports unique
namespace children and avoids known package attribute/dynamic-binding false edges.
These are static file relationships, not complete language runtime binding semantics.

## 11. Security considerations

Preserved public GitHub allowlisting, isolated Git credentials/config/hooks, argument-array
commands, no checkout, no execution, bounded downloads/source, symlink/submodule exclusion
and sanitized worker errors. Config blobs are data only, capped at 64 KiB/file, 64 files,
1 MB total. Iterative glob matching avoids untrusted path recursion. Trusted Host checks
complement same-origin checks; this is still an unauthenticated loopback-only application.

Schema-v2 evidence intentionally persists excerpts, which may contain sensitive public
source text. Privacy/export/deletion documentation now says so explicitly. No new runtime
dependency was added. Container isolation is still recommended for untrusted inputs;
periodic download limits and between-file parser deadlines are not hard OS guarantees.

## 12. Database/migration changes

JSON snapshot schema advances to v2; relational tables remain unchanged, so no new Alembic
revision is needed. Legacy v1 graph/export/impact reads remain supported; architecture
requests return 409 and require reanalysis. Existing snapshots are never rewritten.
SQLite upgrade → downgrade → upgrade → Alembic check and JSON persistence passed.

## 13. Tests added

Deterministic architecture fixture: frontend → API → domain → repository, one intentional
domain → frontend violation, a three-file cycle and an import-reachable candidate test.
Coverage includes config validation/limits/symlinks, conflicts/unknowns, deterministic
cycles and witnesses, alias ambiguity, CommonJS shadowing, Python package false positives,
legacy API behavior, filtering/search/pagination, source snippets and impact bounds.
Frontend covers navigation, filters, violations, cycles, evidence, empty/legacy error
states and safe deletion; browser tests exercise the real API fixture on desktop/mobile.
The fixture is an isolated test adapter, not fabricated production analysis.

## 14. Commands executed

- Git fetch, main fast-forward synchronization, branch/status/log/remote checks; gh auth status.
- `ruff check services tests scripts` and `ruff format --check services tests scripts`.
- `mypy`, `pytest -q`, `python -m build` (inside the existing Python virtual environment).
- `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npm run test:e2e`.
- Migration round trip/check runs within pytest; browser suite starts API and web servers.
- `git diff --check`, license comparison and TODO/FIXME/HACK scan.

## 15. Test results and release gates

Local verification on 2026-09-24: **50 Python tests, 10 component tests and 4 Chromium E2E
tests passed**. Ruff lint/format, strict mypy (16 source modules), frontend lint/typecheck,
Python wheel/sdist and frontend production build passed. The rebuilt source archive was
inspected for Alembic configuration/migrations, requirements and test fixtures; the wheel
was inspected for the new architecture modules. Two upstream Python test-client
deprecation warnings remain. Sandbox process/temp-directory restrictions required approved
native test execution; those startup errors were environmental, not suppressed assertions.

Docker and PostgreSQL executables are unavailable locally. Feature-branch
[CI](https://github.com/dhaneshit008/devlens/actions/runs/35975203811) and
[CodeQL](https://github.com/dhaneshit008/devlens/actions/runs/35975203809) passed for
`b2dd09f42df903f01f53a55168facee0f7f662b3`: PostgreSQL migration round trips, backend/frontend
checks, all browser tests, Docker build/startup and healthy API/web connectivity. Both
Python and JavaScript/TypeScript CodeQL jobs passed; the branch alert query returned no
open findings. The remote SHA was checked directly. A final parser regression also covers
destructured `require` bindings; its targeted test, lint and strict typing passed locally.
Subsequent commit/check state is available in the branch's Actions history.
CodeQL is configured for feature branches and PRs. CI display names now match protected
main's required contexts (`CI / backend`, `CI / frontend`, `CI / browser`, `CI / containers`).
No protection was weakened. The prior dependency-review prerequisite in this report is
obsolete: Dependency graph was enabled and the merged MVP PR's review succeeded.

## 16. Remaining limitations

Single in-process job and one API worker; interrupted jobs fail instead of resuming.
Full snapshot JSON is loaded/validated per query; recent-run listing also loads snapshots.
Cycle detail responses and snapshot exports can still be large. Graph/architecture layouts
are bounded, fixed deterministic layouts, not semantic architecture reconstruction.

No complete TS moduleResolution/exports/extends/project-reference emulation; dynamic
imports/bindings, Python import hooks and runtime calls remain uncertain. File-level
impact is conservative; candidate tests do not represent measured coverage. Unknown layers
and skipped/unsupported files can hide cycles/violations. Directory cycles need not be file
cycles. One witness is shown per component, not every elementary cycle. No private repos,
hosted auth, history, drift comparison, risk probabilities, collaboration or GitHub App.

The Python wheel packages backend modules only; source checkout is the supported full-app
setup. No standalone published CLI or release tag is claimed. Hard worker isolation,
operational limits and broader real-repository resolution coverage remain release priorities.

## 17. Recommended next milestone

v0.6 Risk, beginning with a reviewable methodology for measured complexity/churn/debt
indicators and fixture validation, after v0.5 review. Prioritize worker isolation and
storage projection before shared hosting. Suggested future branch: `feat/devlens-v0.6-risk`.
No v0.6 work has started.
