"""Versioned, evidence-bearing public graph contracts."""

from typing import Literal

from pydantic import BaseModel, Field

from devlens.architecture_models import ArchitectureResult


class SourceLine(BaseModel):
    number: int
    text: str


class Evidence(BaseModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    method: str
    snippet: list[SourceLine] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    kind: Literal["file", "function", "class", "method", "interface"]
    label: str
    path: str
    language: str
    evidence: Evidence
    is_test: bool = False


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: Literal["contains", "imports"]
    evidence: Evidence
    specifier: str | None = None


class Limitation(BaseModel):
    path: str
    line: int
    reason: str
    specifier: str | None = None
    category: str = "unresolved_import"


class Snapshot(BaseModel):
    schema_version: int = 1
    analyzer_version: str
    repository_url: str
    commit_sha: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    languages: dict[str, int]
    skipped: dict[str, int]
    limitations: list[Limitation]
    source_file_count: int
    analyzed_bytes: int
    architecture: ArchitectureResult | None = None
    metrics: dict[str, int] = Field(default_factory=dict)
