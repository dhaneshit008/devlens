"""Test-only API using a real committed fixture. Never imported by the product."""

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from conftest import fixture_repo

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="devlens-e2e-") as temp:
        directory = Path(temp)
        repo = fixture_repo.__wrapped__(directory)
        os.environ["DATABASE_URL"] = "sqlite:///" + str(directory / "e2e.db")
        root = Path(__file__).resolve().parents[1]
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, check=True)
        from devlens import main

        @contextmanager
        def fixture_clone(url, settings):
            if url != "https://github.com/devlens-fixtures/mini-repo":
                raise ValueError("E2E server accepts only its explicit fixture URL.")
            yield repo

        main.clone_public = fixture_clone
        uvicorn.run(main.app, host="127.0.0.1", port=8000)
