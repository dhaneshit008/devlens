"""Evidence-backed layers, directed aggregates, rule violations and import SCCs."""

import posixpath
from collections import defaultdict

from devlens.architecture_models import (
    ArchitectureResult,
    LayerAssignment,
    LayerRelationship,
    Violation,
)
from devlens.architecture_rules import ArchitectureRules, path_matches
from devlens.cycles import dependency_cycles
from devlens.models import GraphEdge, GraphNode

CONVENTIONS = {
    "frontend": "frontend",
    "controllers": "controller",
    "domain": "domain",
    "repositories": "repository",
    "infrastructure": "infrastructure",
    "routes": "api",
    "utils": "utility",
}


def classify(node: GraphNode, config: ArchitectureRules) -> LayerAssignment:
    matches = [
        (layer, pattern)
        for layer, patterns in sorted(config.layers.items())
        for pattern in patterns
        if path_matches(node.path, pattern)
    ]
    layers = {layer for layer, _ in matches}
    if matches:
        return LayerAssignment(
            node_id=node.id,
            path=node.path,
            layer=next(iter(layers)) if len(layers) == 1 else "unknown",
            method="configured path" if len(layers) == 1 else "conflicting configured paths",
            evidence=[f".devlens.json: {layer} = {pattern}" for layer, pattern in matches],
        )
    if node.is_test:
        return LayerAssignment(
            node_id=node.id,
            path=node.path,
            layer="tests",
            method="test naming convention (inferred)",
            evidence=[node.path],
        )
    conventions = sorted({CONVENTIONS[p] for p in node.path.split("/")[:-1] if p in CONVENTIONS})
    return LayerAssignment(
        node_id=node.id,
        path=node.path,
        layer=conventions[0] if len(conventions) == 1 else "unknown",
        method="directory convention (inferred)" if len(conventions) == 1 else "unclassified",
        evidence=[node.path]
        if len(conventions) == 1
        else ["No unique configured or recognized layer."],
    )


def architecture(
    nodes: list[GraphNode], edges: list[GraphEdge], config: ArchitectureRules, configured: bool
) -> ArchitectureResult:
    files = {node.id: node for node in nodes if node.kind == "file"}
    assignments = [classify(files[key], config) for key in sorted(files)]
    by_id = {item.node_id: item.layer for item in assignments}
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    violations: list[Violation] = []
    links: list[tuple[str, str, str]] = []
    directories: list[tuple[str, str, str]] = []
    for edge in sorted(edges, key=lambda item: item.id):
        if edge.kind != "imports":
            continue
        source, target = by_id[edge.source], by_id[edge.target]
        groups[(source, target)].append(edge.id)
        links.append((edge.source, edge.target, edge.id))
        left = posixpath.dirname(files[edge.source].path) or "."
        right = posixpath.dirname(files[edge.target].path) or "."
        if left != right:
            directories.append((left, right, edge.id))
        for rule in config.rules:
            if source != rule.source or target == "unknown":
                continue
            forbidden = (
                target in rule.deny if rule.deny is not None else target not in (rule.allow or [])
            )
            if forbidden:
                violations.append(
                    Violation(
                        id=f"{rule.id}:{edge.id}",
                        edge_id=edge.id,
                        rule_id=rule.id,
                        source_layer=source,
                        target_layer=target,
                    )
                )
    return ArchitectureResult(
        assignments=assignments,
        relationships=[
            LayerRelationship(source=source, target=target, count=len(ids), edge_ids=ids)
            for (source, target), ids in sorted(groups.items())
        ],
        violations=violations,
        cycles=dependency_cycles(links, "file") + dependency_cycles(directories, "directory"),
        rules=config.rules,
        configuration=".devlens.json" if configured else None,
    )
