"""Bounded, typed views over a single persisted snapshot; no invented relationships."""

from pydantic import BaseModel

from devlens.architecture_models import LayerAssignment
from devlens.models import GraphEdge, GraphNode, Limitation, Snapshot


class Page[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int
    truncated: bool
    commit_sha: str


def page[T](items: list[T], snapshot: Snapshot, offset: int, limit: int) -> Page[T]:
    return Page(
        items=items[offset : offset + limit],
        total=len(items),
        offset=offset,
        limit=limit,
        truncated=offset + limit < len(items),
        commit_sha=snapshot.commit_sha,
    )


class GraphPage(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total: int
    offset: int
    limit: int
    truncated: bool
    commit_sha: str
    limitations: list[Limitation]
    limitations_total: int


class Relationship(BaseModel):
    edge: GraphEdge
    source: GraphNode
    target: GraphNode
    source_layer: str
    target_layer: str
    rule_ids: list[str]
    status: str


def relationships(snapshot: Snapshot) -> list[Relationship]:
    nodes = {node.id: node for node in snapshot.nodes}
    layers = (
        {a.node_id: a.layer for a in snapshot.architecture.assignments}
        if snapshot.architecture
        else {}
    )
    violated: dict[str, list[str]] = {}
    if snapshot.architecture:
        for item in snapshot.architecture.violations:
            violated.setdefault(item.edge_id, []).append(item.rule_id)
    return [
        Relationship(
            edge=edge,
            source=nodes[edge.source],
            target=nodes[edge.target],
            source_layer=layers.get(edge.source, "unknown"),
            target_layer=layers.get(edge.target, "unknown"),
            rule_ids=violated.get(edge.id, []),
            status="Violation"
            if edge.id in violated
            else "Unclassified"
            if "unknown" in (layers.get(edge.source, "unknown"), layers.get(edge.target, "unknown"))
            else "No violation detected",
        )
        for edge in sorted(snapshot.edges, key=lambda e: e.id)
        if edge.kind == "imports"
    ]


def search_nodes(snapshot: Snapshot, query: str) -> list[GraphNode]:
    layers: dict[str, LayerAssignment] = (
        {a.path: a for a in snapshot.architecture.assignments} if snapshot.architecture else {}
    )
    cycle_files = (
        {node_id for c in snapshot.architecture.cycles if c.kind == "file" for node_id in c.members}
        if snapshot.architecture
        else set()
    )
    violations = (
        {v.edge_id for v in snapshot.architecture.violations} if snapshot.architecture else set()
    )
    violation_files = {
        node_id
        for edge in snapshot.edges
        if edge.id in violations
        for node_id in (edge.source, edge.target)
    }
    imports: dict[str, list[str]] = {}
    for edge in snapshot.edges:
        if edge.kind == "imports":
            imports.setdefault(edge.source, []).append(edge.specifier or edge.target)
    tokens = []
    for value in query.lower().split():
        key, separator, text = value.partition(":")
        if separator:
            if key not in {"layer", "type", "path", "cycle", "violation", "import"} or not text:
                raise ValueError(
                    "Supported filters: layer:, type:, path:, import:, "
                    "cycle:true/false, violation:true/false."
                )
            if key in {"cycle", "violation"} and text not in {"true", "false"}:
                raise ValueError("cycle: and violation: accept true or false.")
            tokens.append((key, text))
        else:
            tokens.append(("text", value))
    matches = []
    for node in snapshot.nodes:
        file_id = "file:" + node.path
        fields = {
            "text": (node.path + " " + node.label).lower(),
            "path": node.path.lower(),
            "type": node.kind,
            "layer": layers[node.path].layer if node.path in layers else "unknown",
            "cycle": str(file_id in cycle_files).lower(),
            "violation": str(file_id in violation_files).lower(),
            "import": " ".join(imports.get(file_id, [])).lower(),
        }
        if all(
            node.is_test
            if key == "type" and text == "test"
            else text in fields[key]
            if key in {"text", "path", "import"}
            else text == fields[key]
            for key, text in tokens
        ):
            matches.append(node)
    return matches
