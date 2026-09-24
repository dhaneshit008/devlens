"""Data-only tsconfig aliases and conservative static Python package resolution."""

import posixpath
import re
from dataclasses import dataclass, field

from devlens.architecture_rules import strict_json
from devlens.models import Limitation
from devlens.parsers import ImportReference


def strip_json_comments(text: str) -> str:
    # Preserve string literals, including URLs and escaped quotes; strip JSONC comments only.
    token = r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/'
    cleaned = re.sub(token, lambda match: match[0] if match[0].startswith('"') else " ", text)
    return re.sub(
        r'("(?:\\.|[^"\\])*"|,\s*(?=[}\]]))',
        lambda match: match[0] if match[0].startswith('"') else "",
        cleaned,
    )


def safe_path(base: str, value: str) -> str | None:
    if value.startswith("/") or "\\" in value or ":" in value:
        return None
    result = posixpath.normpath(posixpath.join(base, value))
    return None if result == ".." or result.startswith("../") else result


def resolve_javascript(path: str, spec: str, paths: set[str]) -> list[str]:
    if not spec.startswith(("./", "../")):
        return []
    base = safe_path(posixpath.dirname(path), spec)
    return candidates(base, paths) if base is not None else []


def candidate_matches(base: str, paths: set[str]) -> list[str]:
    extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    choices = [base] + [base + ext for ext in extensions]
    choices += [base + "/index" + ext for ext in extensions]
    if base.endswith(".js"):
        choices += [base[:-3] + ".ts", base[:-3] + ".tsx"]
    return sorted(set(choices) & paths)


def candidates(base: str, paths: set[str]) -> list[str]:
    matches = candidate_matches(base, paths)
    return matches if len(matches) == 1 else []


@dataclass
class TSConfig:
    directory: str
    base: str
    has_base: bool
    aliases: dict[str, list[str]] = field(default_factory=dict)
    usable: bool = True


def tsconfigs(configs: dict[str, str]) -> tuple[list[TSConfig], list[Limitation]]:
    result: list[TSConfig] = []
    limitations: list[Limitation] = []
    for path, content in sorted(configs.items()):
        if not path.endswith("tsconfig.json"):
            continue
        directory = posixpath.dirname(path)
        try:
            data = strict_json(strip_json_comments(content))
            if not isinstance(data, dict) or "extends" in data or "references" in data:
                raise ValueError("extends/project references are not resolved")
            options = data.get("compilerOptions", {})
            if not isinstance(options, dict):
                raise ValueError("compilerOptions must be an object")
            base_url = options.get("baseUrl", ".")
            if not isinstance(base_url, str):
                raise ValueError("baseUrl must be a string")
            base = safe_path(directory, base_url)
            aliases = options.get("paths", {})
            if base is None or not isinstance(aliases, dict) or len(aliases) > 128:
                raise ValueError("invalid baseUrl or paths")
            for key, values in aliases.items():
                if (
                    not isinstance(key, str)
                    or len(key) > 200
                    or key.count("*") > 1
                    or not isinstance(values, list)
                    or not 1 <= len(values) <= 16
                    or any(
                        not isinstance(v, str)
                        or len(v) > 200
                        or v.count("*") > 1
                        or ("*" in v and "*" not in key)
                        or safe_path(base, v) is None
                        for v in values
                    )
                ):
                    raise ValueError("path aliases must contain bounded in-repository targets")
            result.append(TSConfig(directory, base, "baseUrl" in options, aliases))
        except (ValueError, TypeError, RecursionError) as exc:
            result.append(TSConfig(directory, directory, False, usable=False))
            limitations.append(
                Limitation(
                    path=path,
                    line=1,
                    category="configuration",
                    reason=f"TS configuration not used: {str(exc)[:120]}",
                )
            )
    return sorted(result, key=lambda item: (-len(item.directory), item.directory)), limitations


def resolve_ts_alias(path: str, spec: str, paths: set[str], configs: list[TSConfig]) -> list[str]:
    config = next(
        (c for c in configs if not c.directory or path.startswith(c.directory + "/")), None
    )
    if config is None or not config.usable:
        return []
    matches: list[tuple[int, str, str]] = []
    for key in config.aliases:
        if "*" not in key:
            if spec == key:
                matches.append((10000, key, ""))
        else:
            prefix, suffix = key.split("*")
            if (
                spec.startswith(prefix)
                and spec.endswith(suffix)
                and len(spec) >= len(prefix) + len(suffix)
            ):
                matches.append(
                    (
                        len(prefix),
                        key,
                        spec[len(prefix) : len(spec) - len(suffix) if suffix else None],
                    )
                )
    if matches:
        best = max(x[0] for x in matches)
        winners = [match for match in matches if match[0] == best]
        if len(winners) != 1:
            return []
        _, key, wildcard = winners[0]
        found: set[str] = set()
        for target in config.aliases[key]:
            base = safe_path(config.base, target.replace("*", wildcard))
            if base is not None:
                options = candidate_matches(base, paths)
                if len(options) > 1:
                    return []
                found.update(options)
        return sorted(found) if len(found) == 1 else []
    base = safe_path(config.base, spec)
    return candidates(base, paths) if config.has_base and base is not None else []


def resolve_python(
    path: str,
    ref: ImportReference,
    paths: set[str],
    package_bindings: dict[str, set[str]] | None = None,
) -> list[str]:
    directory = posixpath.dirname(path)
    root = directory
    depth = 0
    while root and root + "/__init__.py" in paths:
        depth += 1
        root = posixpath.dirname(root)
    if ref.level:
        if ref.level > depth:
            return []
        base = directory
        for _ in range(ref.level - 1):
            base = posixpath.dirname(base)
        bases = [posixpath.join(base, ref.specifier.replace(".", "/")).rstrip("/")]
    else:
        module = ref.specifier.replace(".", "/")
        bases = sorted({module, posixpath.join(root, module), "src/" + module})
    found: set[str] = set()
    viable: list[str] = []
    for base in bases:
        options = {base + ".py", base + "/__init__.py"} & paths
        if len(options) > 1:
            return []
        if options or any(item.startswith(base + "/") for item in paths):
            viable.append(base)
            found.update(options)
    if len(viable) != 1:
        return []
    base = viable[0]
    bindings = (package_bindings or {}).get(base + "/__init__.py", set())
    if ref.names and ({"__getattr__", "*"} & bindings):
        return []
    for name in ref.names:
        if name == "*" or name in (package_bindings or {}).get(base + "/__init__.py", set()):
            continue
        options = {base + "/" + name + ".py", base + "/" + name + "/__init__.py"} & paths
        if len(options) > 1:
            return []
        found.update(options)
    return sorted(found)
