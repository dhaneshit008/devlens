import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    """An actual committed repository; its programs must never run during analysis."""
    repo = tmp_path / "fixture"
    repo.mkdir()
    files = {
        "src/math.ts": "export function add(a: number, b: number) { return a + b; }\n",
        "src/service.ts": "import { add } from './math';\nexport const total = () => add(1, 2);\n",
        "src/ui.tsx": "import { total } from './service';\n"
        "export function App() { return <p>{total()}</p>; }\n",
        "tests/service.test.ts": "import { total } from '../src/service';\n"
        "export const check = () => total();\n",
        "pkg/__init__.py": "",
        "pkg/core.py": "def answer():\n    return 42\n",
        "pkg/client.py": "from .core import answer\nclass Client:\n"
        "    def run(self):\n        return answer()\n",
        "node_modules/nope.js": "throw new Error('must never execute');\n",
        "README.md": "fixture\n",
        "broken.py": "def broken(:\n",
        "binary.py": "\0binary",
    }
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    for args in (
        ["init"],
        ["add", "."],
        [
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)
    return repo
