import json

import pytest
from devlens.analysis import analyze
from devlens.architecture_rules import path_matches, read_rules
from devlens.config import Settings
from devlens.cycles import dependency_cycles
from devlens.impact import impact
from devlens.ingestion import IngestionError, RepositorySource, SourceFile, read_sources
from devlens.models import Snapshot
from devlens.parsers import parse
from devlens.queries import search_nodes


def test_architecture_fixture_evidence_and_determinism(architecture_repo):
    source = read_sources(architecture_repo, Settings())
    result = analyze(source, "https://github.com/fixture/architecture")
    assert result == analyze(source, result.repository_url)
    assert result.schema_version == 2
    architecture = result.architecture
    assert architecture is not None
    assert len(architecture.violations) == 1
    violation = architecture.violations[0]
    edge = next(e for e in result.edges if e.id == violation.edge_id)
    assert (edge.source, edge.target) == ("file:domain/service.ts", "file:frontend/shared.ts")
    assert edge.evidence.snippet[0].text == "import '../frontend/shared';"
    assert edge.evidence.start_line == 1
    assert violation.rule_id == "domain-boundary"
    cycle = next(c for c in architecture.cycles if c.kind == "file")
    assert cycle.path[0] == cycle.path[-1]
    assert len(cycle.edge_ids) == 3
    by_id = {e.id: e for e in result.edges}
    assert [(by_id[e].source, by_id[e].target) for e in cycle.edge_ids] == list(
        zip(cycle.path, cycle.path[1:], strict=False)
    )
    report = impact(result, "file:repository/store.ts")
    assert "domain" in report.affected_layers
    assert report.candidate_tests == ["tests/service.test.ts"]
    assert report.affected_violations
    assert search_nodes(result, "layer:domain cycle:true")
    assert [n.path for n in search_nodes(result, "type:file violation:true path:shared")] == [
        "frontend/shared.ts"
    ]
    assert search_nodes(result, "import:@/repository/store")
    with pytest.raises(ValueError):
        search_nodes(result, "cycle:maybe")


@pytest.mark.parametrize(
    "value",
    [
        {"architecture": {"unknown": []}},
        {"architecture": {"layers": {"domain": ["../escape/**"]}}},
        {"architecture": {"layers": {"unknown": ["**"]}}},
        {
            "architecture": {
                "layers": {"domain": ["domain/**"]},
                "rules": [{"id": "r", "from": "domain", "deny": ["missing"]}],
            }
        },
        {
            "architecture": {
                "layers": {"domain": ["domain/**"]},
                "rules": [{"id": "r", "from": "domain", "allow": [], "deny": []}],
            }
        },
    ],
)
def test_invalid_rules_fail_explicitly(value):
    with pytest.raises(IngestionError, match="Invalid .devlens.json"):
        read_rules({".devlens.json": json.dumps(value)})


def test_duplicate_keys_and_config_code_rejected():
    for text in ('{"architecture": {}, "architecture": {}}', '__import__("os")'):
        with pytest.raises(IngestionError):
            read_rules({".devlens.json": text})


def test_glob_conflict_and_unknown():
    assert path_matches("services/routes/a.py", "services/**/routes/*.py")
    assert not path_matches("services/x/routes/a.py", "services/routes/*.py")
    rules = {"architecture": {"layers": {"api": ["**"], "domain": ["**"]}}}
    result = analyze(
        RepositorySource(
            "a" * 40, [SourceFile("a.py", "Python", "")], {}, {".devlens.json": json.dumps(rules)}
        ),
        "fixture",
    )
    assert result.architecture.assignments[0].layer == "unknown"
    assert result.architecture.assignments[0].method == "conflicting configured paths"


def test_cycles_ignore_acyclic_diamonds_and_handle_self_loop_and_two_nodes():
    assert (
        dependency_cycles(
            [("a", "b", "1"), ("a", "c", "2"), ("b", "d", "3"), ("c", "d", "4")], "file"
        )
        == []
    )
    links = [("a", "b", "1"), ("b", "a", "2"), ("c", "c", "3")]
    cycles = dependency_cycles(links, "file")
    assert [c.members for c in cycles] == [["a", "b"], ["c"]]
    assert cycles == dependency_cycles(list(reversed(links)), "file")


def test_commonjs_static_dynamic_and_shadowed_require():
    parsed = parse(
        SourceFile("a.cjs", "JavaScript", "const x = require('./x'); require(variable);")
    )
    assert [i.specifier for i in parsed.imports] == ["./x"]
    assert len(parsed.limitations) == 1
    for code in (
        "function f(require) { require('./x'); }",
        "const require = f; require('./x');",
        "const { require } = loader; require('./x');",
        "function f({ require }) { require('./x'); }",
    ):
        parsed = parse(SourceFile("a.js", "JavaScript", code))
        assert not parsed.imports and parsed.limitations
    assert (
        parse(SourceFile("a.ts", "TypeScript", "import x = require('./x');")).imports[0].specifier
        == "./x"
    )


def test_aliases_baseurl_ambiguity_and_unsupported_extends():
    files = [
        SourceFile("src/a.ts", "TypeScript", "import '@/b'; import 'b';"),
        SourceFile("src/b.ts", "TypeScript", ""),
    ]
    config = '{ // safe JSONC\n "compilerOptions": {"baseUrl": "src", "paths": {"@/*": ["*"],},},}'
    source = RepositorySource("a" * 40, files, {}, {"tsconfig.json": config})
    result = analyze(source, "fixture")
    assert len([e for e in result.edges if e.kind == "imports"]) == 2
    source.files.append(SourceFile("src/b.js", "JavaScript", ""))
    assert not analyze(source, "fixture").edges
    source.configs["tsconfig.json"] = '{"extends":"./other.json"}'
    result = analyze(source, "fixture")
    assert any(item.category == "configuration" for item in result.limitations)
    assert not result.edges


def test_python_false_edges_and_namespace_packages():
    files = [
        SourceFile("pkg/__init__.py", "Python", "core = 42"),
        SourceFile("pkg/core.py", "Python", ""),
        SourceFile("pkg/client.py", "Python", "from ..outside import x\nfrom pkg import core"),
        SourceFile("outside.py", "Python", ""),
        SourceFile("ns/child.py", "Python", ""),
        SourceFile("client.py", "Python", "from ns import child"),
    ]
    result = analyze(RepositorySource("a" * 40, files, {}), "fixture")
    edges = {(e.source, e.target) for e in result.edges if e.kind == "imports"}
    assert ("file:pkg/client.py", "file:outside.py") not in edges
    assert ("file:pkg/client.py", "file:pkg/core.py") not in edges
    assert ("file:client.py", "file:ns/child.py") in edges
    assert any(item.specifier == "outside" for item in result.limitations)


def test_legacy_snapshot_and_bounded_impact():
    files = [
        SourceFile(f"f{i}.ts", "TypeScript", "" if i == 0 else f"import './f{i - 1}';")
        for i in range(250)
    ]
    result = analyze(RepositorySource("a" * 40, files, {}), "fixture")
    report = impact(result, "file:f0.ts", limit=10)
    assert report.total == 249 and report.truncated
    assert len(report.direct + report.indirect) == 10
    deep = impact(result, "file:f0.ts", offset=220, limit=10)
    assert all(e.path_truncated for e in deep.indirect)
    old = result.model_dump(exclude={"architecture", "metrics"})
    old["schema_version"] = 1
    assert Snapshot.model_validate(old).architecture is None


def test_ambiguous_alias_fallback_and_dynamic_package_do_not_invent_edges():
    files = [
        SourceFile("client.ts", "TypeScript", "import '@/target'; import './target.js';"),
        SourceFile("target.ts", "TypeScript", ""),
        SourceFile("target.js", "JavaScript", ""),
        SourceFile("fallback/target.ts", "TypeScript", ""),
        SourceFile("client.py", "Python", "from pkg import child"),
        SourceFile("pkg/__init__.py", "Python", "def __getattr__(name):\n    return 42"),
        SourceFile("pkg/child.py", "Python", ""),
    ]
    config = json.dumps({"compilerOptions": {"paths": {"@/*": ["*", "fallback/*"]}}})
    result = analyze(RepositorySource("a" * 40, files, {}, {"tsconfig.json": config}), "fixture")
    assert not [edge for edge in result.edges if edge.kind == "imports"]
    assert len(result.limitations) == 3


def test_long_cycles_and_deep_paths_do_not_require_recursive_graph_walks():
    links = [(str(i), str((i + 1) % 1500), str(i)) for i in range(1500)]
    cycle = dependency_cycles(links, "file")[0]
    assert len(cycle.members) == len(cycle.edge_ids) == 1500
    assert cycle.path[0] == cycle.path[-1]
    assert path_matches("/".join(["x"] * 1500 + ["a.py"]), "**/*.py")


def test_config_budget_and_symlink_are_checked_before_reading_blob(monkeypatch, tmp_path):
    from devlens import ingestion

    calls = []

    def fake_read(repo, *args):
        calls.append(args)
        if args[0] == "rev-parse":
            return b"a" * 40
        if args[0] == "ls-tree":
            return b"100644 blob " + b"a" * 40 + b" 65537\t.devlens.json\0"
        raise AssertionError("Oversized configuration must never be read")

    monkeypatch.setattr(ingestion, "git_read", fake_read)
    with pytest.raises(IngestionError, match="configuration exceeds"):
        read_sources(tmp_path, Settings())
    assert len(calls) == 2

    def symlink_read(repo, *args):
        if args[0] == "rev-parse":
            return b"a" * 40
        if args[0] == "ls-tree":
            return b"120000 blob " + b"a" * 40 + b" 20\t.devlens.json\0"
        raise AssertionError("Configuration symlinks must never be read")

    monkeypatch.setattr(ingestion, "git_read", symlink_read)
    result = read_sources(tmp_path, Settings())
    assert not result.configs
    assert result.skipped == {"symlink_or_submodule": 1}


def test_type_file_search_includes_test_files_and_rule_errors_explain_field(architecture_repo):
    result = analyze(read_sources(architecture_repo, Settings()), "fixture")
    assert len(search_nodes(result, "type:file")) == 9
    assert [node.path for node in search_nodes(result, "type:test")] == ["tests/service.test.ts"]
    with pytest.raises(IngestionError, match="Rules must reference explicitly configured layers"):
        read_rules(
            {
                ".devlens.json": json.dumps(
                    {"architecture": {"rules": [{"id": "r", "from": "missing", "deny": []}]}}
                )
            }
        )
