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
