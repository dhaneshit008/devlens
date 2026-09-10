import pytest
from devlens.analysis import analyze, resolve_javascript
from devlens.config import Settings
from devlens.impact import impact
from devlens.ingestion import IngestionError, RepositorySource, SourceFile, read_sources
from devlens.parsers import parse


def test_real_repository_graph_and_evidence(fixture_repo):
    snapshot = analyze(read_sources(fixture_repo, Settings()), "https://github.com/fixture/project")
    assert snapshot.languages == {"Python": 4, "TypeScript": 4}
    assert snapshot.source_file_count == 8
    edges = {(e.source, e.target) for e in snapshot.edges if e.kind == "imports"}
    assert ("file:src/service.ts", "file:src/math.ts") in edges
    assert ("file:pkg/client.py", "file:pkg/core.py") in edges
    symbols = {(n.label, n.kind) for n in snapshot.nodes}
    assert {
        ("add", "function"),
        ("total", "function"),
        ("App", "function"),
        ("Client", "class"),
        ("run", "method"),
    } <= symbols
    assert any(x.path == "broken.py" for x in snapshot.limitations)
    report = impact(snapshot, "file:src/math.ts")
    assert [entry.node.path for entry in report.direct] == ["src/service.ts"]
    assert {entry.node.path for entry in report.indirect} == {"src/ui.tsx", "tests/service.test.ts"}
    assert report.candidate_tests == ["tests/service.test.ts"]
    for entry in report.direct + report.indirect:
        assert entry.evidence_path[0].source == entry.node.id
        assert entry.evidence_path[-1].target == "file:src/math.ts"
        assert all(e.evidence.start_line == 1 for e in entry.evidence_path)
    assert snapshot == analyze(read_sources(fixture_repo, Settings()), snapshot.repository_url)


def test_cycles_diamonds_and_target_exclusion():
    source = RepositorySource(
        "a" * 40,
        [
            SourceFile("a.ts", "TypeScript", "import './b';\n"),
            SourceFile("b.ts", "TypeScript", "import './a';\n"),
            SourceFile("c.ts", "TypeScript", "import './a'; import './b';\n"),
            SourceFile("d.ts", "TypeScript", "import './c';\n"),
        ],
        {},
    )
    report = impact(analyze(source, "https://github.com/a/b"), "file:a.ts")
    assert {x.node.path for x in report.direct} == {"b.ts", "c.ts"}
    assert [x.node.path for x in report.indirect] == ["d.ts"]


def test_comments_strings_and_computed_imports_do_not_become_edges():
    source = SourceFile(
        "a.ts",
        "TypeScript",
        """// import './fake';
const text = "import './fake'";
import('./actual');
import(variable);
export { foo } from './exports';
const require = () => 1; require('./shadowed');
""",
    )
    parsed = parse(source)
    assert [ref.specifier for ref in parsed.imports] == ["./actual", "./exports"]
    assert len(parsed.limitations) == 2


def test_ambiguous_import_is_not_guessed():
    assert resolve_javascript("src/a.ts", "./b", {"src/b.ts", "src/b.js"}) == []
    assert resolve_javascript("src/a.ts", "../../escape", {"escape.ts"}) == []


def test_symbol_scope_is_explicit(fixture_repo):
    snapshot = analyze(read_sources(fixture_repo, Settings()), "https://github.com/a/b")
    node = next(node for node in snapshot.nodes if node.label == "add")
    assert impact(snapshot, node.id).scope == "containing file (conservative)"


def test_python_dynamic_import_reported():
    parsed = parse(SourceFile("a.py", "Python", "importlib.import_module(name)\n"))
    assert len(parsed.limitations) == 1


def test_graph_budget_fails_explicitly():
    source = RepositorySource("a" * 40, [SourceFile("a.ts", "TypeScript", "function a() {}")], {})
    with pytest.raises(IngestionError, match="graph size limit"):
        analyze(source, "https://github.com/a/b", Settings(max_graph_nodes=1))
