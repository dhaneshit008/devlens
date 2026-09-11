# Repository digital twin

Schema v1 contains commit identity, analyzer version, source counts, file and declaration
nodes, typed edges, line evidence, language counts, skipped-entry counts and limitations.
PostgreSQL stores the bounded graph as a JSON document on its analysis run. This keeps
snapshot replacement atomic. It is an initial model, not a general graph database.

`file:path` IDs identify source files; symbol IDs add start row/column and declaration kind.
Containment edges connect files to declarations. Import edges connect files. Future graph
types require explicit extractor evidence and schema evolution, not heuristic UI decoration.

The graph API filters before paging; returned edges have both endpoints inside that page.
The UI states this boundary. It renders at most 100 nodes, with search/type/language filters,
zoom/pan and selection. List view is the accessible alternative. An impact query uses the
entire persisted graph, so its report can include consumers outside the current graph page.
Snapshot export contains the complete bounded result.
