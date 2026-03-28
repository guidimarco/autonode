"""Tests for session cleanup under ../autonode_sessions/."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider


def _touch_dir_old(path: Path, days_ago: float) -> None:
    path.mkdir(parents=True, exist_ok=True)
    old = time.time() - days_ago * 86400
    os.utime(path, (old, old))


@pytest.fixture
def repo_with_sessions(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    sessions = root.parent / "autonode_sessions"
    for name, age in (("stale", 3.0), ("fresh", 0.1)):
        sess = sessions / name
        (sess / "workspace").mkdir(parents=True)
        _touch_dir_old(sess, age)
    return root


def test_cleanup_orphaned_worktrees_removes_only_stale(repo_with_sessions: Path) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(("run", tuple(cmd)))
        return MagicMock(returncode=0, stdout="", stderr="")

    provider = GitWorktreeProvider()
    with patch(
        "autonode.infrastructure.vcs.git_worktree_provider.subprocess.run",
        side_effect=fake_run,
    ):
        with patch(
            "autonode.infrastructure.vcs.git_worktree_provider.shutil.rmtree",
        ) as rmtree:
            removed = provider.cleanup_orphaned_worktrees(str(repo_with_sessions), ttl_days=1)

    stale = repo_with_sessions.parent / "autonode_sessions" / "stale"
    assert str(stale) in removed
    assert len(removed) == 1
    worktree_removes = [c for c in calls if c[0] == "run" and "remove" in c[1]]
    assert len(worktree_removes) >= 1
    assert any(str(stale) in str(cmd) for _, cmd in worktree_removes)
    prunes = [c for c in calls if c[0] == "run" and "prune" in c[1]]
    assert len(prunes) == 1
    rmtree.assert_called()


def test_cleanup_orphaned_worktrees_empty_root(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    provider = GitWorktreeProvider()
    assert provider.cleanup_orphaned_worktrees(str(repo), ttl_days=1) == []


def test_remove_all_session_worktrees(repo_with_sessions: Path) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(("run", tuple(cmd)))
        return MagicMock(returncode=0, stdout="", stderr="")

    provider = GitWorktreeProvider()
    with patch(
        "autonode.infrastructure.vcs.git_worktree_provider.subprocess.run",
        side_effect=fake_run,
    ):
        with patch("autonode.infrastructure.vcs.git_worktree_provider.shutil.rmtree"):
            provider.remove_all_session_worktrees(str(repo_with_sessions))

    prunes = [c for c in calls if c[0] == "run" and "prune" in c[1]]
    assert len(prunes) == 1
    removes = [c for c in calls if c[0] == "run" and "remove" in c[1]]
    assert len(removes) >= 2
