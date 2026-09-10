"""Construct deterministic file/declaration graphs with conservative import resolution."""

import posixpath
import time
from collections import Counter
from pathlib import PurePosixPath

from devlens import __version__
from devlens.config import Settings
from devlens.ingestion import IngestionError, RepositorySource
from devlens.models import Evidence, GraphEdge, GraphNode, Limitation, Snapshot
from devlens.parsers import ImportReference, parse


def is_test_file(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        "tests" in p.parts
        or "__tests__" in p.parts
        or p.name.startswith("test_")
        or p.name.endswith("_test.py")
        or ".test." in p.name
        or ".spec." in p.name
    )


def resolve_javascript(path: str, spec: str, paths: set[str]) -> list[str]:
    if not spec.startswith(("./", "../")):
        return []
    base = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
    if base.startswith("../") or base.startswith("/"):
        return []
    if base in paths:
        return [base]
    candidates = [base + ext for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")]
    candidates += [base + "/index" + ext for ext in (".ts", ".tsx", ".js", ".jsx")]
    if base.endswith(".js"):
        candidates += [base[:-3] + ".ts", base[:-3] + ".tsx"]
    matches = sorted(set(candidates) & paths)
    # Ambiguous candidates depend on toolchain resolution settings; never guess.
    return matches if len(matches) == 1 else []


def resolve_python(path: str, ref: ImportReference, paths: set[str]) -> list[str]:
    directory = posixpath.dirname(path)
    root = directory
    while root and root + "/__init__.py" in paths:
        root = posixpath.dirname(root)
    if ref.level:
        base = directory
        for _ in range(ref.level - 1):
            if not base:
                return []
            base = posixpath.dirname(base)
        # Relative imports require a package context.
        if directory + "/__init__.py" not in paths:
            return []
        module = posixpath.join(base, ref.specifier.replace(".", "/"))
        bases = [module]
    else:
        module = ref.specifier.replace(".", "/")
        bases = sorted({module, posixpath.join(root, module), "src/" + module})

    matches: list[str] = []
    for base in bases:
        candidates = [base + ".py", base.rstrip("/") + "/__init__.py"]
        found = [candidate for candidate in candidates if candidate in paths]
        if len(found) > 1:
            return []
        if found:
            matches.extend(found)
    if len(set(matches)) > 1:
        return []
    # from package import module also depends on a statically present submodule.
    submodules: list[str] = []
    for name in ref.names:
        if name == "*":
            continue
        submodule_matches = {posixpath.join(base, name) + ".py" for base in bases} & paths
        if len(submodule_matches) == 1:
            submodules.extend(submodule_matches)
    return sorted(set(matches + submodules))


def analyze(
    source: RepositorySource, repository_url: str, limits: Settings | None = None
) -> Snapshot:
    limits = limits or Settings()
    started = time.monotonic()
    paths = {file.path for file in source.files}
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    limitations: list[Limitation] = []
    for file in sorted(source.files, key=lambda f: f.path):
        if time.monotonic() - started > limits.max_analysis_seconds:
            raise IngestionError("Repository parsing exceeded the time limit.")
        file_id = "file:" + file.path
        evidence = Evidence(
            path=file.path,
            start_line=1,
            end_line=max(1, len(file.content.splitlines())),
            method="git blob",
        )
        nodes.append(
            GraphNode(
                id=file_id,
                kind="file",
                label=file.path,
                path=file.path,
                language=file.language,
                evidence=evidence,
                is_test=is_test_file(file.path),
            )
        )
        parsed = parse(file)
        nodes.extend(parsed.symbols)
        limitations.extend(parsed.limitations)
        for symbol in parsed.symbols:
            edges.append(
                GraphEdge(
                    id="contains:" + symbol.id,
                    source=file_id,
                    target=symbol.id,
                    kind="contains",
                    evidence=symbol.evidence,
                )
            )
        for index, ref in enumerate(parsed.imports):
            targets = (
                resolve_python(file.path, ref, paths)
                if file.language == "Python"
                else resolve_javascript(file.path, ref.specifier, paths)
            )
            if not targets:
                limitations.append(
                    Limitation(
                        path=file.path,
                        line=ref.line,
                        specifier=ref.specifier,
                        reason="External, unsupported or ambiguous import; no internal edge.",
                    )
                )
            for target in targets:
                edges.append(
                    GraphEdge(
                        id=f"import:{file.path}:{index}:{target}",
                        source=file_id,
                        target="file:" + target,
                        kind="imports",
                        evidence=Evidence(
                            path=file.path,
                            start_line=ref.line,
                            end_line=ref.end_line,
                            method="AST literal import + static path resolution",
                        ),
                    )
                )
        if len(nodes) > limits.max_graph_nodes or len(edges) > limits.max_graph_edges:
            raise IngestionError("Repository exceeds the graph size limit.")
    return Snapshot(
        analyzer_version=__version__,
        repository_url=repository_url,
        commit_sha=source.commit_sha,
        nodes=nodes,
        edges=edges,
        languages=dict(sorted(Counter(f.language for f in source.files).items())),
        skipped=source.skipped,
        limitations=limitations,
        source_file_count=len(source.files),
        analyzed_bytes=sum(len(f.content.encode("utf-8")) for f in source.files),
    )
