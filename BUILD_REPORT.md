# DevLens build report

## Completed

The v0.1–v0.4 local workflow is implemented: safe public repository ingestion, language
detection, AST declarations/imports, persisted digital twin, interactive explorer and
evidence-backed change impact. The original Apache-2.0 license is byte-for-byte preserved.

## Testing

- 30 Python tests passed: URL/environment isolation, Git object reads, dirty-worktree
  exclusion, symlink rejection, resource budgets, parser semantics, graph/impact,
  API lifecycle and migration upgrade/downgrade/upgrade with snapshot persistence.
- 4 frontend component tests passed.
- 2 Chromium end-to-end tests passed: full analysis/evidence/deletion flow and mobile layout.
- Python lint/format, strict mypy, frontend lint/typecheck and production build passed.
- Python sdist/wheel build passed. npm audit reported zero vulnerabilities after Vitest update.
- Actual public ingestion smoke test: `psf/requests` at
  `dae7ef63b4df6eded86637f251fc4e3a06c3b479`: 37 files, 844 nodes, 130 import edges,
  209 explicitly reported resolution/extraction limitations. This is an observed test,
  not a benchmark. Source was not checked out or executed.
- Dark/light UI screenshots were inspected; fixtures are labeled in README.md.
- The local analysis helper was smoke-tested against committed DevLens source, including
  impact output and rejection of a missing target and a non-repository directory.
- [GitHub CI](https://github.com/dhaneshit008/devlens/actions/runs/34607929678) passed for
  `a3ab49c3f3712c3889b66e12dc5c87df4bf4e080`: backend checks with PostgreSQL migration
  round trips, frontend checks, Chromium browser tests, and Docker build/startup with
  API and web connectivity. [CodeQL](https://github.com/dhaneshit008/devlens/actions/runs/34607929713)
  passed for Python and JavaScript/TypeScript at the same commit.

## Architecture

React/Vite/TypeScript/Tailwind/React Flow; FastAPI modular monolith; Tree-sitter JS/TS
and Python AST; SQLAlchemy and Alembic; PostgreSQL reference database with explicit
SQLite local/test mode. No AI API dependency, Redis, extra backend service or empty SDK.

## Git

Repository: `dhaneshit008/devlens`. Work prepared on `feat/devlens-mvp` with separate
Conventional Commits for specification, ingestion/storage, analysis, API/UI and operations.
Native Git and GitHub CLI authentication are available as `dhaneshit008`; the existing
specification, backend and frontend commits have been verified on the remote branch.
Publication uses Git with the authenticated GitHub CLI credential helper. Final remote state
and CI outcomes are recorded in the session completion report; this file does not
claim an external action before it has been verified.

## Current version

0.4.0 development build; no release tag or public hosted deployment.

## Experimental features and known limitations

Import path resolution is conservative. Symbol impact uses its containing file. CommonJS,
aliases, namespace packages, runtime calls, API/database inference and private repositories
are not supported. Candidate tests use naming plus reachability; no coverage is claimed.
History, risk, health scoring and architecture-rule engines remain planned.

One in-process analysis job and one API worker are supported. Jobs interrupted by restart
become failed. The graph uses bounded JSON snapshots and fixed grid placement. Downloads
have periodic size checks; native parsing is not preempted inside a source file.

## Security notes

Public GitHub HTTPS allowlist; isolated credential/config environment; disabled hooks,
redirects and prompting; no checkout or execution; skipped symlinks/submodules; resource
limits; same-origin browser checks; deletion support; non-root constrained containers.
The service is unauthenticated and local-only. Compose PostgreSQL trust authentication
is restricted to its internal development network and must be replaced before shared hosting.

## Environment limits and remaining gate

Docker and PostgreSQL executables were unavailable on the local Windows machine.
SQLite migrations and persistence were tested locally; PostgreSQL and Docker startup
were subsequently verified by the successful GitHub CI run linked above.
Two upstream Python test-client deprecation warnings remain; they are not test failures.

[Dependency review](https://github.com/dhaneshit008/devlens/actions/runs/34607931334) is
blocked by repository configuration: GitHub reports that Dependency graph must be enabled.
The authenticated CLI can push, but the available browser is not signed in to change this
setting. Enable Dependency graph in repository Settings → Advanced Security, then rerun
the failed dependency-review job. The workflow remains enforced; it has not been skipped.

Broader import-resolution fixtures and harder worker isolation remain priorities before
a public release.
