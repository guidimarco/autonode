"""Risoluzione repo sotto REPOS_ROOT."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.infrastructure.paths.repo_resolution import ensure_git_repo_under_root


@pytest.fixture
def fake_repos_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    r = tmp_path / "src"
    r.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.REPOS_ROOT", str(r))
    return r


def test_resolve_relative_under_root(fake_repos_root: Path) -> None:
    ab = fake_repos_root / "a" / "b"
    ab.mkdir(parents=True)
    (ab / ".git").mkdir()
    p = ensure_git_repo_under_root("a/b")
    assert p == ab.resolve()


def test_resolve_rejects_parent_escape(fake_repos_root: Path) -> None:
    with pytest.raises(ValueError, match="repo_path outside of REPOS_ROOT"):
        ensure_git_repo_under_root("../outside")


def test_resolve_absolute_under_root(fake_repos_root: Path) -> None:
    proj = fake_repos_root / "proj"
    proj.mkdir()
    (proj / ".git").mkdir()
    p = ensure_git_repo_under_root(str(proj))
    assert p == proj.resolve()
