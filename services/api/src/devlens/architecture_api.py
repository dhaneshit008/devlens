"""Typed paginated architecture queries over immutable, versioned snapshots."""

from collections import Counter, defaultdict, deque
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from devlens.architecture_models import ArchitectureResult, DependencyCycle, LayerAssignment
from devlens.architecture_rules import Rule
from devlens.models import Limitation, Snapshot
from devlens.queries import Page, Relationship, page, relationships

Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Text = Annotated[str, Query(max_length=300)]


class LayerCount(BaseModel):
    source: str
    target: str
    count: int


class ArchitectureSummary(BaseModel):
    commit_sha: str
    configuration: str | None
    direction: str = "consumer → dependency"
    layers: dict[str, int]
    relationships: list[LayerCount]
    rules: list[Rule]
    metrics: dict[str, int]


class CycleDetail(BaseModel):
    commit_sha: str
    cycle: DependencyCycle
    relationships: list[Relationship]


def require_architecture(snapshot: Snapshot) -> ArchitectureResult:
    if snapshot.architecture is None:
        raise HTTPException(
            409, "This legacy snapshot has no architecture data. Analyze the repository again."
        )
    return snapshot.architecture


def create_architecture_router(load: Callable[[str], Snapshot]) -> APIRouter:
    router = APIRouter(prefix="/api/v1/analysis/{run_id}")

    @router.get("/architecture", response_model=ArchitectureSummary)
    def overview(run_id: str) -> ArchitectureSummary:
        snapshot = load(run_id)
        result = require_architecture(snapshot)
        return ArchitectureSummary(
            commit_sha=snapshot.commit_sha,
            configuration=result.configuration,
            layers=dict(sorted(Counter(a.layer for a in result.assignments).items())),
            relationships=[
                LayerCount(source=r.source, target=r.target, count=r.count)
                for r in result.relationships
            ],
            rules=result.rules,
            metrics=snapshot.metrics,
        )

    @router.get("/architecture/layers", response_model=Page[LayerAssignment])
    def layers(
        run_id: str, layer: Text = "", path: Text = "", offset: Offset = 0, limit: Limit = 50
    ) -> Page[LayerAssignment]:
        snapshot = load(run_id)
        result = require_architecture(snapshot)
        return page(
            [
                a
                for a in result.assignments
                if (not layer or a.layer == layer) and path.lower() in a.path.lower()
            ],
            snapshot,
            offset,
            limit,
        )

    @router.get("/relationships", response_model=Page[Relationship])
    @router.get("/architecture/violations", response_model=Page[Relationship])
    def related(
        run_id: str,
        request: Request,
        source_layer: Text = "",
        target_layer: Text = "",
        rule: Text = "",
        path: Text = "",
        language: Text = "",
        status: Literal["", "violation", "unclassified", "no violation detected"] = "",
        offset: Offset = 0,
        limit: Limit = 50,
    ) -> Page[Relationship]:
        snapshot = load(run_id)
        require_architecture(snapshot)
        items = [
            r
            for r in relationships(snapshot)
            if (not source_layer or r.source_layer == source_layer)
            and (not request.url.path.endswith("/violations") or bool(r.rule_ids))
            and (not target_layer or r.target_layer == target_layer)
            and (not rule or rule in r.rule_ids)
            and path.lower() in (r.source.path + " " + r.target.path).lower()
            and (not language or r.source.language == language)
            and (not status or r.status.lower() == status)
        ]
        return page(items, snapshot, offset, limit)

    @router.get("/cycles", response_model=Page[DependencyCycle])
    def cycles(
        run_id: str,
        kind: Literal["", "file", "directory"] = "",
        path: Text = "",
        offset: Offset = 0,
        limit: Limit = 50,
    ) -> Page[DependencyCycle]:
        snapshot = load(run_id)
        result = require_architecture(snapshot)
        return page(
            [
                c
                for c in result.cycles
                if (not kind or c.kind == kind)
                and any(path.lower() in member.lower() for member in c.members)
            ],
            snapshot,
            offset,
            limit,
        )

    @router.get("/cycles/{cycle_id}", response_model=CycleDetail)
    def cycle_detail(run_id: str, cycle_id: str) -> CycleDetail:
        snapshot = load(run_id)
        result = require_architecture(snapshot)
        cycle = next((c for c in result.cycles if c.id == cycle_id), None)
        if cycle is None:
            raise HTTPException(404, "Cycle not found.")
        by_edge = {r.edge.id: r for r in relationships(snapshot)}
        return CycleDetail(
            commit_sha=snapshot.commit_sha,
            cycle=cycle,
            relationships=[by_edge[key] for key in cycle.edge_ids],
        )

    @router.get("/limitations", response_model=Page[Limitation])
    def limitations(
        run_id: str, category: Text = "", offset: Offset = 0, limit: Limit = 50
    ) -> Page[Limitation]:
        snapshot = load(run_id)
        return page(
            [item for item in snapshot.limitations if not category or item.category == category],
            snapshot,
            offset,
            limit,
        )

    @router.get("/dependencies", response_model=Page[Relationship])
    def dependencies(
        run_id: str,
        target: str,
        direction: Literal["incoming", "outgoing"] = "outgoing",
        depth: Literal["direct", "transitive"] = "direct",
        offset: Offset = 0,
        limit: Limit = 50,
    ) -> Page[Relationship]:
        snapshot = load(run_id)
        node = next((n for n in snapshot.nodes if n.id == target), None)
        if node is None:
            raise HTTPException(404, "Target node not found.")
        adjacency: dict[str, list[Relationship]] = defaultdict(list)
        for item in relationships(snapshot):
            adjacency[item.edge.source if direction == "outgoing" else item.edge.target].append(
                item
            )
        seen = {"file:" + node.path}
        queue = deque(seen)
        found: dict[str, Relationship] = {}
        while queue:
            current = queue.popleft()
            for item in adjacency[current]:
                found[item.edge.id] = item
                neighbor = item.edge.target if direction == "outgoing" else item.edge.source
                if depth == "transitive" and neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        return page([found[key] for key in sorted(found)], snapshot, offset, limit)

    return router
