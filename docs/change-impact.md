# Change impact

`imports` points consumer → dependency. A reverse breadth-first traversal from the
target file discovers consumers. Distance 1 is direct; distance >1 is transitive.
A visited set prevents cycles and duplicate counts. Sorted adjacency makes output
deterministic. For a diamond, the report gives one shortest evidence path, not every
possible route. Containment edges are never included in dependency traversal.

Each result contains the consumer node, hop distance, observed/inferred classification
and ordered import edges from consumer to target. UI links point to the source range
at the analyzed commit. The selected target is excluded from its own impact radius.

Symbol selections map to the containing file and are labeled conservative. Candidate
tests are reachable files named `test_*`, `*_test.py`, `*.test.*`, `*.spec.*`, or inside
`tests`/`__tests__`. This is test discovery, not test execution or coverage measurement.

Zero consumers means none were found in the analyzed graph. It does not establish
safety: unresolved imports, skipped files, runtime dispatch and external consumers can
hide dependencies. Direct imports establish a source relationship, not that every edit
to the imported module affects the consumer. There are no AI confidence percentages.

## v0.5 architecture context and response bounds

Impact now includes known layers touched by the target/reachable consumers, existing
cycle groups and existing violation IDs intersecting that surface, plus the selected
file's outgoing direct dependency paths. These are existing relationships, not newly
predicted violations. Incoming dependents and outgoing dependencies retain distinct labels.

`offset`/`limit` page the breadth-first result (maximum 100). `direct_count`,
`indirect_count`, `total`, candidate tests and architecture context refer to the whole
reachable graph, not just the page. Each shortest evidence path is capped at 200 hops,
with a 4,000-edge aggregate response budget; `path_truncated` explicitly signals an
incomplete path. Export the snapshot for full graph inspection. Predecessor indexes
avoid constructing quadratic copies of every path before paging.
