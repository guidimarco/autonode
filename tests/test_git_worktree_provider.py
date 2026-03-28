"""GitWorktreeProvider: repository Git obbligatorio (nessuna modalità senza VCS)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider

_VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


def test_setup_session_worktree_requires_dot_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_src = tmp_path / "src"
    fake_src.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.REPOS_ROOT", str(fake_src))
    norepo = fake_src / "norepo"
    norepo.mkdir(parents=True)
    provider = GitWorktreeProvider()
    with pytest.raises(ValueError, match="Git repository"):
        provider.setup_session_worktree(_VALID_UUID, "norepo")
