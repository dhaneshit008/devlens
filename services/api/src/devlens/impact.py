"""Potential change surface, not runtime breakage prediction."""

from collections import defaultdict, deque

from pydantic import BaseModel

from devlens.models import GraphEdge, GraphNode, Snapshot


class ImpactEntry(BaseModel):
    node: GraphNode
    distance: int
    classification: str
    evidence_path: list[GraphEdge]


class ImpactReport(BaseModel):
    target: GraphNode
    scope: str
    direct: list[ImpactEntry]
    indirect: list[ImpactEntry]
    candidate_tests: list[str]
    limitations: list[str]


def impact(snapshot: Snapshot, target_id: str) -> ImpactReport:
    nodes = {n.id: n for n in snapshot.nodes}
    if target_id not in nodes:
        raise KeyError(target_id)
    target = nodes[target_id]
    start = "file:" + target.path
    incoming: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in snapshot.edges:
        if edge.kind == "imports":
            incoming[edge.target].append(edge)
    queue: deque[tuple[str, list[GraphEdge]]] = deque([(start, [])])
    seen = {start}
    entries: list[ImpactEntry] = []
    while queue:
        current, trail = queue.popleft()
        for edge in sorted(incoming[current], key=lambda e: (e.source, e.id)):
            if edge.source in seen:
                continue
            seen.add(edge.source)
            route = [edge, *trail]
            entries.append(
                ImpactEntry(
                    node=nodes[edge.source],
                    distance=len(route),
                    classification="observed import"
                    if len(route) == 1
                    else "inferred reachability",
                    evidence_path=route,
                )
            )
            queue.append((edge.source, route))
    return ImpactReport(
        target=target,
        scope="file" if target.kind == "file" else "containing file (conservative)",
        direct=[entry for entry in entries if entry.distance == 1],
        indirect=[entry for entry in entries if entry.distance > 1],
        candidate_tests=[entry.node.path for entry in entries if entry.node.is_test],
        limitations=[
            "Static imports show possible change propagation, not guaranteed runtime breakage.",
            "Symbol selections use file dependencies; symbol references are not resolved.",
            "Candidate tests are import-reachable files named like tests, not measured coverage.",
            f"Snapshot has {len(snapshot.limitations)} extraction/resolution limitations. "
            "Skipped files may hide consumers.",
        ],
    )
