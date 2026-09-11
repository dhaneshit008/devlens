"""Run with DEVLENS_TEST_DATABASE_URL to validate against a disposable PostgreSQL DB."""

import os
import subprocess
import sys

from devlens.storage import AnalysisRun
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session


def test_migration_upgrade_downgrade_upgrade(tmp_path):
    url = os.environ.get("DEVLENS_TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "migration.db"))
    env = {**os.environ, "DATABASE_URL": url}
    for command in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"], ["check"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *command], env=env, check=True, capture_output=True
        )
    engine = create_engine(url)
    assert "analysis_runs" in inspect(engine).get_table_names()
    with Session(engine) as session:
        row = AnalysisRun(
            id="db-roundtrip",
            repository_url="https://github.com/fixture/repo",
            status="completed",
            stage="completed",
            snapshot={"nodes": [], "unicode": "λ"},
        )
        session.add(row)
        session.commit()
        session.expire_all()
        persisted = session.get(AnalysisRun, "db-roundtrip")
        assert persisted.snapshot == {"nodes": [], "unicode": "λ"}
        session.delete(persisted)
        session.commit()
    engine.dispose()
