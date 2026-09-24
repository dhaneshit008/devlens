"""Construct deterministic file/declaration graphs with conservative import resolution."""

import time
from collections import Counter
from pathlib import PurePosixPath

from devlens import __version__
from devlens.architecture import architecture
from devlens.architecture_rules import read_rules
from devlens.config import Settings
from devlens.ingestion import IngestionError, RepositorySource
from devlens.models import Evidence, GraphEdge, GraphNode, Limitation, Snapshot, SourceLine
from devlens.parsers import parse
from devlens.resolution import resolve_javascript, resolve_python, resolve_ts_alias, tsconfigs


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


def analyze(
    source: RepositorySource, repository_url: str, limits: Settings | None = None
) -> Snapshot:
    limits = limits or Settings()
    started = time.monotonic()
    rules = read_rules(source.configs)
    aliases, configuration_limits = tsconfigs(source.configs)
    parsed_files = {}
    declaration_count = 0
    for file in source.files:
        if time.monotonic() - started > limits.max_analysis_seconds:
            raise IngestionError("Repository parsing exceeded the time limit.")
        parsed_files[file.path] = parse(file)
        declaration_count += len(parsed_files[file.path].symbols)
        if declaration_count + len(source.files) > limits.max_graph_nodes:
            raise IngestionError("Repository exceeds the graph size limit.")
    package_bindings = {
        path: result.bindings
        for path, result in parsed_files.items()
        if path.endswith("/__init__.py")
    }
    js_paths = {file.path for file in source.files if file.language != "Python"}
    py_paths = {file.path for file in source.files if file.language == "Python"}
    lines = {file.path: file.content.splitlines() for file in source.files}
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    limitations: list[Limitation] = list(configuration_limits)
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
        parsed = parsed_files[file.path]
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
                resolve_python(file.path, ref, py_paths, package_bindings)
                if file.language == "Python"
                else (
                    resolve_javascript(file.path, ref.specifier, js_paths)
                    if ref.specifier.startswith(("./", "../"))
                    else resolve_ts_alias(file.path, ref.specifier, js_paths, aliases)
                )
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
                        specifier=ref.specifier,
                        evidence=Evidence(
                            path=file.path,
                            start_line=ref.line,
                            end_line=ref.end_line,
                            method=ref.mechanism + " + static path resolution",
                        ),
                    )
                )
        if len(nodes) > limits.max_graph_nodes or len(edges) > limits.max_graph_edges:
            raise IngestionError("Repository exceeds the graph size limit.")
    for evidence in [*(node.evidence for node in nodes), *(edge.evidence for edge in edges)]:
        start = evidence.start_line - 1
        evidence.snippet = [
            SourceLine(number=start + index + 1, text=line[:240])
            for index, line in enumerate(
                lines[evidence.path][start : min(evidence.end_line, start + 5)]
            )
        ]
    for item in limitations:
        reason = item.reason.lower()
        if "parse failed" in reason or "syntax" in reason:
            item.category = "parse_error"
        elif "computed" in reason or "dynamic" in reason or "binding" in reason:
            item.category = "dynamic_import"
    architecture_result = architecture(nodes, edges, rules, ".devlens.json" in source.configs)
    return Snapshot(
        schema_version=2,
        architecture=architecture_result,
        metrics={
            "declarations": sum(node.kind != "file" for node in nodes),
            "resolved_import_edges": sum(edge.kind == "imports" for edge in edges),
            "unresolved_imports": sum(
                item.category in {"unresolved_import", "dynamic_import"} for item in limitations
            ),
            "parse_errors": sum(item.category == "parse_error" for item in limitations),
            "candidate_test_files": sum(node.is_test for node in nodes),
            "layers": len(
                {item.layer for item in architecture_result.assignments if item.layer != "unknown"}
            ),
            "violations": len(architecture_result.violations),
            "file_cycle_groups": sum(c.kind == "file" for c in architecture_result.cycles),
            "directory_cycle_groups": sum(
                c.kind == "directory" for c in architecture_result.cycles
            ),
        },
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
