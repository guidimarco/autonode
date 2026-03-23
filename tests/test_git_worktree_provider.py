"""GitWorktreeProvider: repository Git obbligatorio (nessuna modalità senza VCS)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider


def test_setup_session_worktree_requires_dot_git(tmp_path: Path) -> None:
    provider = GitWorktreeProvider()
    with pytest.raises(RuntimeError, match=r"\.git assente"):
        provider.setup_session_worktree("session-x", str(tmp_path))
