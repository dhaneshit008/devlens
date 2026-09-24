"""Strict, bounded architecture configuration. Repository configuration is data only."""

import json
import re
from fnmatch import fnmatchcase
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from devlens.ingestion import IngestionError


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    source: str = Field(alias="from")
    allow: list[str] | None = Field(default=None, max_length=32)
    deny: list[str] | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def one_policy(self) -> Self:
        if (self.allow is None) == (self.deny is None):
            raise ValueError("Specify exactly one of allow or deny.")
        return self


class ArchitectureRules(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    layers: dict[str, list[str]] = Field(default_factory=dict, max_length=32)
    rules: list[Rule] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        for name, patterns in self.layers.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", name) or name == "unknown":
                raise ValueError("Layer names must be lowercase identifiers; unknown is reserved.")
            if not 1 <= len(patterns) <= 32:
                raise ValueError("Each layer requires 1–32 path patterns.")
            for pattern in patterns:
                if (
                    not pattern
                    or len(pattern) > 200
                    or pattern.startswith("/")
                    or "\\" in pattern
                    or ":" in pattern
                    or any(part in {"", ".", ".."} for part in pattern.split("/"))
                ):
                    raise ValueError("Patterns must be bounded repository-relative paths.")
        if len({rule.id for rule in self.rules}) != len(self.rules):
            raise ValueError("Rule IDs must be unique.")
        for rule in self.rules:
            referenced = [rule.source, *(rule.allow or []), *(rule.deny or [])]
            if any(name not in self.layers for name in referenced):
                raise ValueError("Rules must reference explicitly configured layers.")
        return self


class RepositoryRules(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    architecture: ArchitectureRules


def strict_json(content: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate configuration key.")
            result[key] = value
        return result

    return json.loads(content, object_pairs_hook=pairs)


def read_rules(configs: dict[str, str]) -> ArchitectureRules:
    if ".devlens.json" not in configs:
        return ArchitectureRules()
    try:
        return RepositoryRules.model_validate(strict_json(configs[".devlens.json"])).architecture
    except ValidationError as exc:
        error = exc.errors(include_input=False, include_url=False)[0]
        location = ".".join(str(part) for part in error["loc"])
        detail = f"{location}: {error['msg']}"[:240]
        raise IngestionError(f"Invalid .devlens.json architecture configuration: {detail}") from exc
    except (ValueError, RecursionError) as exc:
        detail = str(exc).splitlines()[0][:180]
        raise IngestionError(f"Invalid .devlens.json architecture configuration: {detail}") from exc


def path_matches(path: str, pattern: str) -> bool:
    """Slash-separated globs: * matches one segment, ** matches zero or more."""
    parts, patterns = path.split("/"), pattern.split("/")

    # Iterative dynamic programming avoids recursion on deeply nested untrusted paths.
    previous = [True] + [False] * len(parts)
    for pattern_part in patterns:
        current = [previous[0] and pattern_part == "**"] + [False] * len(parts)
        for index, part in enumerate(parts, 1):
            current[index] = (
                previous[index] or current[index - 1]
                if pattern_part == "**"
                else previous[index - 1] and fnmatchcase(part, pattern_part)
            )
        previous = current
    return previous[-1]
