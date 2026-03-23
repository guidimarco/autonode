"""Tests for session worktree cleanup under .autonode/worktrees/."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autonode.infrastructure.vcs import workspace_cleanup


def _touch_dir_old(path: Path, days_ago: float) -> None:
    path.mkdir(parents=True)
    old = time.time() - days_ago * 86400
    os.utime(path, (old, old))


@pytest.fixture
def repo_with_worktrees(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    wt_root = root / ".autonode" / "worktrees"
    _touch_dir_old(wt_root / "stale", 3.0)
    _touch_dir_old(wt_root / "fresh", 0.1)
    return root


def test_cleanup_orphaned_worktrees_removes_only_stale(repo_with_worktrees: Path) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(("run", tuple(cmd)))
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch(
        "autonode.infrastructure.vcs.workspace_cleanup.subprocess.run",
        side_effect=fake_run,
    ):
        with patch(
            "autonode.infrastructure.vcs.workspace_cleanup.shutil.rmtree",
        ) as rmtree:
            removed = workspace_cleanup.cleanup_orphaned_worktrees(
                str(repo_with_worktrees), ttl_days=1
            )

    stale = repo_with_worktrees / ".autonode" / "worktrees" / "stale"
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
    assert workspace_cleanup.cleanup_orphaned_worktrees(str(repo), ttl_days=1) == []


def test_cleanup_all_session_worktrees(repo_with_worktrees: Path) -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        calls.append(("run", tuple(cmd)))
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch(
        "autonode.infrastructure.vcs.workspace_cleanup.subprocess.run",
        side_effect=fake_run,
    ):
        with patch("autonode.infrastructure.vcs.workspace_cleanup.shutil.rmtree"):
            removed = workspace_cleanup.cleanup_all_session_worktrees(str(repo_with_worktrees))

    assert len(removed) == 2
    prunes = [c for c in calls if c[0] == "run" and "prune" in c[1]]
    assert len(prunes) == 1
