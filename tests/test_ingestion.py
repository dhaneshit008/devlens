import subprocess
from pathlib import Path

import pytest
from devlens.config import Settings
from devlens.ingestion import IngestionError, canonical_url, git_env, read_sources


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://github.com.evil/a/b",
        "https://user:pass@github.com/a/b",
        "https://github.com:443/a/b",
        "https://github.com/a/..",
        "https://github.com/a/b?x=1",
        "https://github.com/a/b#main",
        "file:///tmp/repo",
        "https://127.0.0.1/a/b",
        "https://github.com/a/b/tree/main",
        "https://github.com/a/b%2f..",
        "https://github.com/a/b?",
    ],
)
def test_reject_untrusted_urls(url):
    with pytest.raises(IngestionError):
        canonical_url(url)


def test_url_canonicalization():
    assert canonical_url("https://github.com/owner/repo.git/") == "https://github.com/owner/repo"


def test_git_environment_drops_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "do-not-leak")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("SSH_AUTH_SOCK", "secret")
    env = git_env(tmp_path)
    assert (
        "GITHUB_TOKEN" not in env and "GIT_CONFIG_COUNT" not in env and "SSH_AUTH_SOCK" not in env
    )
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_reads_commit_not_dirty_worktree(fixture_repo):
    (fixture_repo / "src/math.ts").write_text("throw new Error('dirty');")
    source = read_sources(fixture_repo, Settings())
    assert len(source.commit_sha) == 40
    assert next(f.content for f in source.files if f.path == "src/math.ts").startswith(
        "export function"
    )
    assert source.skipped == {
        "binary_or_non_utf8": 1,
        "generated_or_vendor": 1,
        "unsupported_language": 1,
    }


def test_budgets_fail_without_silent_truncation(fixture_repo):
    with pytest.raises(IngestionError, match="source analysis budget"):
        read_sources(fixture_repo, Settings(max_files=1))
    with pytest.raises(IngestionError, match="tree entry limit"):
        read_sources(fixture_repo, Settings(max_tree_entries=1))
    source = read_sources(fixture_repo, Settings(max_file_bytes=1))
    assert source.skipped["oversized_file"] > 0


def test_symlink_blob_not_followed(fixture_repo: Path):
    # Write a Git symlink directly; works even on Windows without symlink privilege.
    oid = (
        subprocess.run(
            ["git", "-C", str(fixture_repo), "hash-object", "-w", "--stdin"],
            input=b"../../outside.py",
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(fixture_repo),
            "update-index",
            "--add",
            "--cacheinfo",
            f"120000,{oid},escape.py",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(fixture_repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "symlink",
        ],
        check=True,
        capture_output=True,
    )
    source = read_sources(fixture_repo, Settings())
    assert source.skipped["symlink_or_submodule"] == 1
    assert "escape.py" not in {file.path for file in source.files}
