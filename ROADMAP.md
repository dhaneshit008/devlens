# Roadmap

Milestones are acceptance gates, not promises that files alone constitute completion.

| Version | Scope | Acceptance |
| --- | --- | --- |
| 0.1.0 | Foundation | React, FastAPI, PostgreSQL migrations, Docker, safe public ingestion and language counts |
| 0.2.0 | Repository intelligence | AST declarations and imports, deterministic graph, parser fixtures |
| 0.3.0 | Digital twin | Persisted graph API, interactive explorer, evidence and node details |
| 0.4.0 | Change intelligence | Reverse direct/transitive impact, candidate tests, evidence paths and UI |
| 0.5.0 | Architecture | Implemented development scope: strict JSON rules, explainable layers, directed map, cycle witnesses, violations and source evidence; see build report for gates |
| 0.6.0 | Risk | Documented churn/complexity/debt heuristics, no invented probabilities |
| 0.7.0 | History | Evolution, blame and evidence-backed historical context |
| 0.8.0 | Collaboration | Historical familiarity, contribution paths, concentration |
| 0.9.0 | GitHub App | Auth, signed webhooks, PR checks, minimum permissions |
| 1.0.0 | Community | Stable APIs, CLI, plugin contract, self-hosting and DevLens dogfooding |

Read CHANGELOG.md and the build report for what is actually validated. Hosted deployment,
release tags and release automation wait until reproducibility and operational checks pass.

The next planned product milestone is v0.6 Risk. First define and validate transparent
complexity/churn/debt measures on real repositories; do not derive probabilities from
import reachability. Resolver coverage, hard worker isolation and storage projections
remain prerequisites for broader use, not claims of completed future milestones.
