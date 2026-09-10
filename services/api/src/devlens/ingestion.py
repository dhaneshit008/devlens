"""Bounded Git object ingestion. Analyzed source is never checked out or executed."""

import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from devlens.config import Settings


class IngestionError(ValueError):
    """A safe, user-visible ingestion failure."""


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.query
        or parsed.fragment
        or "?" in value
        or "#" in value
    ):
        raise IngestionError(
            "Use https://github.com/owner/repository without credentials or options."
        )
    path = parsed.path.removesuffix("/").removesuffix(".git")
    if not re.fullmatch(r"/[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", path):
        raise IngestionError("Invalid GitHub owner or repository name.")
    if path.rsplit("/", 1)[1] in {".", ".."}:
        raise IngestionError("Invalid repository name.")
    return "https://github.com" + path


def git_env(home: Path) -> dict[str, str]:
    # Preserve executable lookup and OS essentials, never credentials or Git config.
    env = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    env.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "XDG_CONFIG_HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_ALLOW_PROTOCOL": "https",
        }
    )
    # Some portable Git distributions put helpers in mingw64/bin.
    import shutil

    executable = shutil.which("git")
    if executable:
        helper = Path(executable).parent.parent / "mingw64" / "bin"
        if (helper / "git-remote-https.exe").exists():
            env["GIT_EXEC_PATH"] = str(helper)
    return env


def git_args(*args: str) -> list[str]:
    return [
        "git",
        "-c",
        "core.hooksPath=" + os.devnull,
        "-c",
        "credential.helper=",
        "-c",
        "http.followRedirects=false",
        "-c",
        "protocol.file.allow=never",
        "-c",
        "protocol.ext.allow=never",
        *args,
    ]


def git_read(repo: Path, *args: str, timeout: int = 20) -> bytes:
    try:
        return subprocess.run(
            git_args("-C", str(repo), *args),
            env=git_env(repo.parent),
            capture_output=True,
            check=True,
            timeout=timeout,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise IngestionError("Could not read repository Git objects.") from exc


@contextmanager
def clone_public(url: str, limits: Settings) -> Iterator[Path]:
    remote = canonical_url(url)
    with tempfile.TemporaryDirectory(prefix="devlens-") as directory:
        root = Path(directory)
        repo = root / "repository"
        started = time.monotonic()
        try:
            with subprocess.Popen(
                git_args(
                    "clone",
                    "--depth=1",
                    "--single-branch",
                    "--no-tags",
                    "--no-checkout",
                    "--",
                    remote + ".git",
                    str(repo),
                ),
                env=git_env(root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=os.name != "nt",
            ) as process:
                try:
                    while process.poll() is None:
                        if time.monotonic() - started > limits.max_clone_seconds:
                            raise IngestionError("Repository fetch exceeded the time limit.")
                        size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
                        if size > limits.max_repository_bytes:
                            raise IngestionError("Repository exceeds the download size limit.")
                        time.sleep(0.1)
                    if process.returncode:
                        raise IngestionError(
                            "Public repository fetch failed. Check its URL and access."
                        )
                    if (
                        sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
                        > limits.max_repository_bytes
                    ):
                        raise IngestionError("Repository exceeds the download size limit.")
                finally:
                    if process.poll() is None:
                        if sys.platform == "win32":
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                capture_output=True,
                                check=False,
                            )
                        else:
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
            yield repo
        except OSError as exc:
            raise IngestionError(
                "Git is unavailable or temporary repository storage failed."
            ) from exc


LANGUAGES = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
}
IGNORED = {"node_modules", "vendor", ".venv", "venv", "dist", "build", ".git", "__pycache__"}


@dataclass(frozen=True)
class SourceFile:
    path: str
    language: str
    content: str


@dataclass
class RepositorySource:
    commit_sha: str
    files: list[SourceFile]
    skipped: dict[str, int]


def read_sources(repo: Path, limits: Settings) -> RepositorySource:
    sha = git_read(repo, "rev-parse", "HEAD").decode().strip()
    # ls-tree reads metadata only; no paths from the repository become filesystem writes.
    entries = git_read(repo, "ls-tree", "-r", "-l", "-z", "HEAD").split(b"\0")
    if len(entries) - 1 > limits.max_tree_entries:
        raise IngestionError("Repository exceeds the tree entry limit.")
    files: list[SourceFile] = []
    skipped: dict[str, int] = {}
    total = 0

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, object_id, raw_size = metadata.split()
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError:
            skip("non_utf8_path")
            continue
        parts = path.split("/")
        if (
            any(part in {"..", ".", ""} for part in parts)
            or "\\" in path
            or any(ord(c) < 32 for c in path)
        ):
            skip("unsafe_path")
            continue
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            skip("symlink_or_submodule")
            continue
        if any(part in IGNORED for part in parts):
            skip("generated_or_vendor")
            continue
        language = LANGUAGES.get(Path(path).suffix)
        if language is None:
            skip("unsupported_language")
            continue
        size = int(raw_size)
        if size > limits.max_file_bytes:
            skip("oversized_file")
            continue
        if len(files) >= limits.max_files or total + size > limits.max_source_bytes:
            raise IngestionError(
                "Repository exceeds the source analysis budget; use a smaller repository."
            )
        content = git_read(repo, "cat-file", "blob", object_id.decode())
        try:
            decoded = content.decode("utf-8")
            if "\0" in decoded:
                raise UnicodeError()
        except UnicodeError:
            skip("binary_or_non_utf8")
            continue
        total += size
        files.append(SourceFile(path, language, decoded))
    return RepositorySource(sha, files, skipped)
