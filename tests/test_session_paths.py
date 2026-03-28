"""Session host paths: autonode_sessions layout."""

from __future__ import annotations

from pathlib import Path

from autonode.core.sandbox.session_paths import outputs_host, session_root_host, worktree_host


def test_session_paths_layout() -> None:
    repo = Path("/home/user/myproject")
    sid = "abc-123"
    expected_root = (repo.parent / "autonode_sessions" / sid).resolve()
    assert session_root_host(str(repo), sid) == str(expected_root)
    assert worktree_host(str(repo), sid) == str(expected_root / "workspace")
    assert outputs_host(str(repo), sid) == str(expected_root / "outputs")


def test_session_root_when_repo_is_app_uses_volume() -> None:
    assert session_root_host("/app", "x") == "/autonode_sessions/x"
