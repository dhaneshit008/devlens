from contextlib import contextmanager

import pytest
from devlens import main
from devlens.ingestion import IngestionError
from devlens.storage import AnalysisRun, Base, make_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client(tmp_path, monkeypatch, fixture_repo):
    engine = make_engine("sqlite:///" + str(tmp_path / "api.db"))
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "Session", session)
    monkeypatch.setattr(main, "engine", engine)

    @contextmanager
    def fixture_clone(url, settings):
        yield fixture_repo

    monkeypatch.setattr(main, "clone_public", fixture_clone)
    with TestClient(main.app, base_url="http://localhost") as test_client:
        yield test_client
    engine.dispose()


def test_analysis_graph_impact_and_deletion_roundtrip(client):
    response = client.post(
        "/api/v1/analysis", json={"repository_url": "https://github.com/fixture/repo"}
    )
    assert response.status_code == 202
    run_id = response.json()["id"]
    prefix = f"/api/v1/analysis/{run_id}"
    row = client.get(prefix).json()
    assert row["status"] == "completed", row
    assert row["summary"]["source_file_count"] == 8
    assert client.get("/api/v1/analysis").json()[0]["id"] == run_id
    graph = client.get(prefix + "/graph?kind=file&limit=2").json()
    assert graph["total"] == 8 and len(graph["nodes"]) == 2 and graph["truncated"]
    filtered = client.get(prefix + "/graph?q=math&kind=function").json()
    assert filtered["total"] == 1
    report = client.get(prefix + "/impact", params={"target": "file:src/math.ts"}).json()
    assert len(report["direct"]) == 1 and len(report["indirect"]) == 2
    assert client.get(prefix + "/snapshot").json()["commit_sha"] == row["summary"]["commit_sha"]
    assert client.get(prefix + "/impact?target=missing").status_code == 404
    assert client.get(prefix + "/graph?limit=501").status_code == 422
    assert client.delete(prefix).status_code == 204
    assert client.get(prefix).status_code == 404


def test_invalid_requests_cannot_start_ingestion(client):
    assert client.get("/api/v1/health", headers={"Origin": "http://localhost"}).status_code == 200
    assert (
        client.post("/api/v1/analysis", json={"repository_url": "file:///etc"}).status_code == 422
    )
    assert (
        client.post(
            "/api/v1/analysis",
            headers={"Origin": "https://evil.example"},
            json={"repository_url": "https://github.com/a/b"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/analysis/nope/graph").status_code == 404


def test_failure_persisted_and_capacity_released(client, monkeypatch):
    def failed(*args):
        raise IngestionError("Repository fetch exceeded the time limit.")

    monkeypatch.setattr(main, "clone_public", failed)
    response = client.post("/api/v1/analysis", json={"repository_url": "https://github.com/a/b"})
    row = client.get("/api/v1/analysis/" + response.json()["id"]).json()
    assert row["status"] == "failed" and "time limit" in row["error"]
    assert not main.admission.locked()
    assert client.get(f"/api/v1/analysis/{row['id']}/graph").status_code == 409


def test_backpressure(client):
    main.admission.acquire()
    try:
        response = client.post(
            "/api/v1/analysis", json={"repository_url": "https://github.com/a/b"}
        )
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "5"
    finally:
        main.admission.release()


def test_restart_marks_interrupted_jobs_failed(tmp_path, monkeypatch):
    engine = make_engine("sqlite:///" + str(tmp_path / "restart.db"))
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "Session", session)
    with session.begin() as db:
        db.add(
            AnalysisRun(
                id="interrupted",
                repository_url="https://github.com/a/b",
                status="running",
                stage="fetching",
            )
        )
    with TestClient(main.app, base_url="http://localhost") as client:
        assert client.get("/api/v1/analysis/interrupted").json()["status"] == "failed"
    engine.dispose()


def test_untrusted_host_rejected_even_when_origin_matches(client):
    assert (
        client.get(
            "/api/v1/analysis", headers={"Host": "evil.example", "Origin": "http://evil.example"}
        ).status_code
        == 400
    )


def test_architecture_api_queries(client, monkeypatch, architecture_repo):
    @contextmanager
    def clone(url, settings):
        yield architecture_repo

    monkeypatch.setattr(main, "clone_public", clone)
    created = client.post(
        "/api/v1/analysis", json={"repository_url": "https://github.com/fixture/architecture"}
    )
    prefix = "/api/v1/analysis/" + created.json()["id"]
    summary = client.get(prefix + "/architecture").json()
    assert summary["metrics"]["violations"] == 1
    assert summary["direction"] == "consumer → dependency"
    assert summary["configuration"] == ".devlens.json"
    layers = client.get(prefix + "/architecture/layers?layer=domain&limit=2").json()
    assert layers["total"] == 4 and layers["truncated"]
    assert all(item["layer"] == "domain" for item in layers["items"])
    violations = client.get(prefix + "/architecture/violations").json()
    assert violations["total"] == 1
    assert client.get(prefix + "/relationships?status=violation").json()["total"] == 1
    assert (
        client.get(prefix + "/relationships?status=no%20violation%20detected").json()["total"] == 7
    )
    assert client.get(prefix + "/relationships?status=invented").status_code == 422
    item = violations["items"][0]
    assert item["edge"]["evidence"]["snippet"][0]["number"] == 1
    assert item["rule_ids"] == ["domain-boundary"]
    assert client.get(prefix + "/architecture/violations?language=Python").json()["total"] == 0
    assert (
        client.get(prefix + "/relationships?source_layer=frontend&target_layer=api").json()["total"]
        == 1
    )
    cycles = client.get(prefix + "/cycles?kind=file").json()
    assert cycles["total"] == 1
    cycle = client.get(prefix + "/cycles/" + cycles["items"][0]["id"]).json()
    assert len(cycle["relationships"]) == 3
    assert client.get(prefix + "/cycles/missing").status_code == 404
    impact = client.get(
        prefix + "/impact", params={"target": "file:repository/store.ts", "limit": 1}
    ).json()
    assert impact["truncated"] and impact["affected_layers"]
    assert client.get(prefix + "/graph?q=cycle:maybe").status_code == 422
    assert client.get(prefix + "/graph?q=layer:domain&kind=file").json()["total"] == 4
    assert client.get(prefix + "/limitations?limit=101").status_code == 422
    dependencies = client.get(
        prefix + "/dependencies",
        params={"target": "file:frontend/view.ts", "direction": "outgoing", "depth": "transitive"},
    ).json()
    assert dependencies["total"] == 4
    assert client.get(prefix + "/dependencies?target=missing").status_code == 404


def test_legacy_snapshot_architecture_requires_reanalysis(client):
    response = client.post(
        "/api/v1/analysis", json={"repository_url": "https://github.com/fixture/repo"}
    )
    run_id = response.json()["id"]
    with main.Session.begin() as session:
        row = session.get(AnalysisRun, run_id)
        old = dict(row.snapshot)
        old.pop("architecture")
        old.pop("metrics")
        old["schema_version"] = 1
        row.snapshot = old
    assert client.get(f"/api/v1/analysis/{run_id}/architecture").status_code == 409
    assert client.get(f"/api/v1/analysis/{run_id}/graph").status_code == 200
    assert (
        client.get(f"/api/v1/analysis/{run_id}/impact?target=file:src/math.ts").status_code == 200
    )
