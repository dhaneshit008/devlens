"""Persisted architecture findings reference original import-edge evidence."""

from typing import Literal

from pydantic import BaseModel, Field

from devlens.architecture_rules import Rule


class LayerAssignment(BaseModel):
    node_id: str
    path: str
    layer: str
    method: str
    evidence: list[str]


class LayerRelationship(BaseModel):
    source: str
    target: str
    count: int
    edge_ids: list[str]


class Violation(BaseModel):
    id: str
    edge_id: str
    rule_id: str
    source_layer: str
    target_layer: str


class DependencyCycle(BaseModel):
    id: str
    kind: Literal["file", "directory"]
    members: list[str]
    path: list[str]
    edge_ids: list[str]


class ArchitectureResult(BaseModel):
    assignments: list[LayerAssignment] = Field(default_factory=list)
    relationships: list[LayerRelationship] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    cycles: list[DependencyCycle] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)
    configuration: str | None = None
