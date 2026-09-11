# ADR 0001 — local evidence-first modular monolith

Status: accepted for the initial MVP.

## Context

The first value is an inspectable repository graph and change surface. Accurate source
evidence and reproducible development matter more than distributed infrastructure or AI.

## Decisions and alternatives

- **FastAPI/Python modular monolith:** parser and graph modules are ordinary Python
  libraries. Multiple services would add deployment overhead before measured need.
- **PostgreSQL + Alembic:** one transactional run/snapshot store with explicit migrations.
  SQLite is an explicit local/test option. A graph database would add operational cost;
  bounded graph documents are enough for the first traversal queries.
- **Tree-sitter JS/TS + Python AST:** real grammars instead of regex semantics. Python's
  built-in parser gives well-defined declarations/imports; Tree-sitter supports TSX/JSX.
  A language-server/typechecker resolver would improve precision at higher complexity.
- **React Flow:** maintained graph controls and keyboard support plus a separate list
  view. Cytoscape was considered; the initial UI needs React node details and selection
  more than graph-algorithm plugins. Fixed grid positions are deterministic, not inferred
  architecture layers. A dependency-aware layout is a future usability improvement.
- **No AI dependency:** deterministic results exist first. A provider interface should
  be introduced only with an implemented evidence-grounded interpretation use case.
- **Single in-process job:** admission control and persisted failure states keep local
  operation understandable. Durable background workers are required before multi-user hosting.

## Consequences

This is intentionally a bounded local product. It cannot claim runtime call precision,
private-repository isolation, high-throughput jobs or complete import resolution. New
analyzers must emit the same evidence contract and contribute deterministic fixtures.
