# Analysis engine

Input is a public GitHub URL or a local Git repository explicitly supplied to the local
script. A shallow public clone contains a single HEAD snapshot. Reads use `ls-tree` and
`cat-file` with object IDs; there is no source checkout, dependency install, import of
the target code, hook execution, submodule recursion or LFS execution.

## Extraction

Python uses `ast.parse`: named classes, sync/async functions and methods, `import` and
`from` statements. JavaScript/TypeScript use the packaged Tree-sitter grammars: named
functions, function-valued variable declarations, classes, interfaces and methods;
ES imports, re-exports and literal `import()` expressions. Location ranges are 1-based.
IDs use relative path, start position and kind; they are deterministic within a snapshot
but are not a promise of stable identity across line moves.

## Resolution

Relative JS/TS imports resolve only to a unique analyzed candidate: exact paths,
supported extensions or directory index files. A `.js` specifier may map to a unique
`.ts`/`.tsx` source. Ambiguity produces a limitation. Bare packages, tsconfig aliases,
package export maps, escaped strings, computed imports and CommonJS are not resolved.
CommonJS `require` may be locally shadowed; recording it as confirmed without binding
analysis would create false edges.

Python absolute imports consider repository-root, `src/` and an observed package root.
Relative imports require an `__init__.py` package context. `from package import child`
can include a present child module. Namespace packages, sys.path manipulation,
conditional runtime binding, import hooks, implicit parent-package initialization and
attribute/submodule shadowing are not fully modeled. These are static path relationships,
not a proof of Python's runtime binding. Dynamic Python imports are reported unresolved.

No call graph, API route inference, database mapping, inheritance resolution or
cross-language invocation edges are asserted in this version. Test flags use filenames
and directory names only. Comments and string contents do not become import statements.

## Bounds and incompleteness

Defaults: 90s clone, approximately 200 MB Git storage, 20,000 tree entries, 2,000 source
files, 500 KB/file, 20 MB source, 180s parser traversal budget (checked between files),
20,000 graph nodes and 50,000 edges. Per-object Git reads have a 20s timeout. Clone disk
checks are periodic and may overshoot briefly; use OS/container limits for hard isolation.
Native parsing cannot be preempted within one file by the between-file deadline.

Unsupported extensions, generated/vendor directories, symlinks, submodules, binary or
non-UTF-8 input, unsafe paths and oversized files are skipped with counts. Repository
or graph budget overflow fails the run. Syntax failures are explicit limitations.
An empty supported-source set is a valid empty snapshot, never a fake populated dashboard.
No source body is persisted, but symbol names/import specifiers and paths are metadata.

Tests include real committed repositories, dirty working trees, symlink Git entries,
malicious URLs, cycles, diamond graphs, external/ambiguous imports and API persistence.
The source uses [Python AST](https://docs.python.org/3/library/ast.html),
[Tree-sitter](https://tree-sitter.github.io/py-tree-sitter/) and
[React Flow](https://reactflow.dev/learn) through their documented interfaces.
