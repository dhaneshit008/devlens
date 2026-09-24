"""Potential change surface, not runtime breakage prediction."""

import posixpath
from collections import defaultdict, deque

from pydantic import BaseModel, Field

from devlens.models import GraphEdge, GraphNode, Snapshot


class ImpactEntry(BaseModel):
    node: GraphNode
    distance: int
    classification: str
    evidence_path: list[GraphEdge]
    path_truncated: bool = False


class ImpactReport(BaseModel):
    target: GraphNode
    scope: str
    direct: list[ImpactEntry]
    indirect: list[ImpactEntry]
    candidate_tests: list[str]
    limitations: list[str]
    direct_count: int = 0
    indirect_count: int = 0
    total: int = 0
    offset: int = 0
    limit: int = 100
    truncated: bool = False
    affected_layers: list[str] = Field(default_factory=list)
    affected_cycles: list[str] = Field(default_factory=list)
    affected_rules: list[str] = Field(default_factory=list)
    affected_violations: list[str] = Field(default_factory=list)
    outgoing_dependencies: list[str] = Field(default_factory=list)


def impact(snapshot: Snapshot, target_id: str, offset: int = 0, limit: int = 100) -> ImpactReport:
    nodes = {n.id: n for n in snapshot.nodes}
    if target_id not in nodes:
        raise KeyError(target_id)
    target = nodes[target_id]
    start = "file:" + target.path
    incoming: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in snapshot.edges:
        if edge.kind == "imports":
            incoming[edge.target].append(edge)
    queue = deque([start])
    seen = {start}
    predecessor: dict[str, GraphEdge] = {}
    distance = {start: 0}
    discovered: list[str] = []
    while queue:
        current = queue.popleft()
        for edge in sorted(incoming[current], key=lambda e: (e.source, e.id)):
            if edge.source in seen:
                continue
            seen.add(edge.source)
            predecessor[edge.source] = edge
            distance[edge.source] = distance[current] + 1
            discovered.append(edge.source)
            queue.append(edge.source)
    entries: list[ImpactEntry] = []
    budget = 4000
    for node_id in discovered[offset : offset + limit]:
        route: list[GraphEdge] = []
        cursor = node_id
        while cursor != start and len(route) < 200 and budget:
            edge = predecessor[cursor]
            route.append(edge)
            cursor = edge.target
            budget -= 1
        entries.append(
            ImpactEntry(
                node=nodes[node_id],
                distance=distance[node_id],
                classification="observed import"
                if distance[node_id] == 1
                else "inferred reachability",
                evidence_path=route,
                path_truncated=cursor != start,
            )
        )
    architecture = snapshot.architecture
    directories = {posixpath.dirname(nodes[node_id].path) or "." for node_id in seen}
    edge_by_id = {edge.id: edge for edge in snapshot.edges}
    return ImpactReport(
        target=target,
        direct_count=sum(distance[node_id] == 1 for node_id in discovered),
        indirect_count=sum(distance[node_id] > 1 for node_id in discovered),
        total=len(discovered),
        offset=offset,
        limit=limit,
        truncated=offset + limit < len(discovered),
        affected_layers=sorted({a.layer for a in architecture.assignments if a.node_id in seen})
        if architecture
        else [],
        affected_cycles=[
            c.id
            for c in architecture.cycles
            if set(c.members) & (seen if c.kind == "file" else directories)
        ]
        if architecture
        else [],
        affected_rules=sorted(
            {
                v.rule_id
                for v in architecture.violations
                if edge_by_id[v.edge_id].source in seen or edge_by_id[v.edge_id].target in seen
            }
        )
        if architecture
        else [],
        affected_violations=[
            v.id
            for v in architecture.violations
            if edge_by_id[v.edge_id].source in seen or edge_by_id[v.edge_id].target in seen
        ]
        if architecture
        else [],
        outgoing_dependencies=sorted(
            {
                nodes[e.target].path
                for e in snapshot.edges
                if e.kind == "imports" and e.source == start
            }
        ),
        scope="file" if target.kind == "file" else "containing file (conservative)",
        direct=[entry for entry in entries if entry.distance == 1],
        indirect=[entry for entry in entries if entry.distance > 1],
        candidate_tests=[nodes[node_id].path for node_id in discovered if nodes[node_id].is_test],
        limitations=[
            "Results are paginated; evidence paths are capped at 200 hops and 4,000 edges "
            "per response. A truncated path is explicitly labeled.",
            "Static imports show possible change propagation, not guaranteed runtime breakage.",
            "Symbol selections use file dependencies; symbol references are not resolved.",
            "Candidate tests are import-reachable files named like tests, not measured coverage.",
            f"Snapshot has {len(snapshot.limitations)} extraction/resolution limitations. "
            "Skipped files may hide consumers.",
        ],
    )
