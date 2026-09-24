# DevLens AI — product specification

Creator and lead maintainer: Dhanesh M V. License: existing Apache-2.0.

DevLens turns a public GitHub repository at a concrete commit into an inspectable
repository digital twin. Developers explore source structure and import relationships,
then inspect the potential consequences of a change. No LLM key is required.

## First delivery: v0.1–v0.4

1. Accept only canonical public `https://github.com/owner/repository` URLs.
2. Obtain a bounded, shallow Git snapshot without checking out or executing source.
3. Detect TypeScript, JavaScript and Python; extract declarations and literal imports
   from syntax trees. Preserve unresolved imports and parse errors as limitations.
4. Persist commit identity, graph, analysis version, evidence and run status.
5. Provide an accessible React explorer with search, filters, pan, zoom, node details,
   source evidence links and a tabular alternative.
6. Calculate direct and transitive import dependents, with shortest evidence paths.
   A symbol selection conservatively uses its containing file; label this explicitly.
7. Support reproducible local development, PostgreSQL migrations, tests and CI.

## Phase 2: v0.5 Architecture Intelligence

Add strict repository-defined `.devlens.json` layers and allow/deny policies, conservative
classification evidence, resolved-import violations, file/directory SCCs with real closed
witnesses, directed architecture maps, side-by-side source evidence and categorized
limitations. Improve static CommonJS, safe tsconfig aliases/baseUrl and Python packages.
All views share one persisted, versioned snapshot. Preserve consumer → dependency
semantics, expose uncertainty and never fabricate metrics, severity or runtime effects.

## Acceptance

Enter a public URL → observe progress → inspect a committed snapshot → select a file
or declaration → inspect direct/indirect dependents and their evidence. Tests use
deterministic fixture repositories. Counts must come from actual analysis. Empty,
partial, unsupported and failed results must be distinct. Delete persisted analysis. Open Architecture, inspect configured/inferred layers, drill
into a violation and cycle edge, then inspect affected layers/cycles/rules during impact.
An explicit deterministic architecture fixture verifies this workflow.

## Boundaries

This is a local, single-user MVP. Hosted authentication, private repositories, runtime
call graphs, complete module-resolution semantics, risk predictions, health scores, historical
intelligence, AI explanations and GitHub automation are later milestones. No fabricated
charts or placeholder navigation. Import reachability is a possible change surface,
not a guarantee that a change breaks code. Tests inferred from file names are candidates,
not measured coverage. Limits and uncertainty are part of every snapshot.

## Quality gates

Python lint, strict type checking, unit/integration tests and package build; frontend
lint, type checking, component tests and production build; migration round trips;
security tests for malicious URLs, symlinks, budgets and source handling. Container
and browser verification are reported separately when the environment cannot run them.
