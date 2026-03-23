"""
Remove session worktrees under ``.autonode/worktrees/`` by age or wholesale cleanup.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


def _worktrees_root(repo_path: Path) -> Path:
    return (repo_path / ".autonode" / "worktrees").resolve()


def _path_age_seconds(path: Path) -> float:
    st = path.stat()
    birth = getattr(st, "st_birthtime", None)
    ts = float(birth) if birth is not None else float(st.st_mtime)
    return max(0.0, time.time() - ts)


def _git_worktree_remove(repo: Path, worktree_dir: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)


def _git_worktree_prune(repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"],
        check=False,
        capture_output=True,
        text=True,
    )


def cleanup_orphaned_worktrees(repo_path: str, ttl_days: int = 1) -> list[str]:
    """
    Under ``<repo>/.autonode/worktrees/``, remove directories older than ``ttl_days``.

    Uses directory birth time when available, else mtime. Each removal is attempted via
    ``git worktree remove --force`` then ``shutil.rmtree`` if needed; ends with
    ``git worktree prune`` once on ``repo_path``.
    """
    repo = Path(repo_path).resolve()
    root = _worktrees_root(repo)
    if not root.is_dir():
        return []

    ttl_seconds = max(0, ttl_days) * 86400
    removed: list[str] = []

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if _path_age_seconds(child) <= ttl_seconds:
            continue
        _git_worktree_remove(repo, child)
        removed.append(str(child))

    if removed:
        _git_worktree_prune(repo)
    return removed


def cleanup_all_session_worktrees(repo_path: str) -> list[str]:
    """
    Remove every session directory under ``.autonode/worktrees/``, then ``git worktree prune``.
    """
    repo = Path(repo_path).resolve()
    root = _worktrees_root(repo)
    if not root.is_dir():
        return []

    removed: list[str] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        _git_worktree_remove(repo, child)
        removed.append(str(child))

    _git_worktree_prune(repo)
    return removed
