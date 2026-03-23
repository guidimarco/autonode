"""Tests for path_guard sandbox resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools.path_guard import PathGuard, resolve_under_root, resolved_root


def test_resolved_root_expands_and_resolves(tmp_path: Path) -> None:
    sub = tmp_path / "proj"
    sub.mkdir()
    r = resolved_root(str(sub))
    assert r == sub.resolve()


def test_resolve_under_root_accepts_dot(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    got = resolve_under_root(str(root), ".")
    assert got == root.resolve()


def test_resolve_under_root_nested_path(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    (root / "a" / "b").mkdir(parents=True)
    got = resolve_under_root(str(root), "a/b")
    assert got == (root / "a" / "b").resolve()


def test_resolve_under_root_rejects_absolute_path(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    with pytest.raises(ValueError, match="path assoluto"):
        resolve_under_root(str(root), str(tmp_path / "other"))


def test_resolve_under_root_blocks_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    with pytest.raises(ValueError, match="fuori dalla sandbox"):
        resolve_under_root(str(root), "..")


def test_resolve_under_root_blocks_traversal_via_nested_dotdot(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "inside").mkdir()
    with pytest.raises(ValueError, match="fuori dalla sandbox"):
        resolve_under_root(str(root), "inside/../../..")


def test_path_guard_rejects_host_runtime(tmp_path: Path) -> None:
    env = ExecutionEnvironmentModel(
        session_id="s",
        sandbox_id="host-runtime",
        worktree_host_path=str(tmp_path),
        container_workspace_path="/workspace",
    )
    with pytest.raises(ValueError, match="host-runtime"):
        PathGuard(env)


def test_path_guard_rejects_empty_worktree() -> None:
    env = ExecutionEnvironmentModel(
        session_id="s",
        sandbox_id="container-id",
        worktree_host_path="   ",
        container_workspace_path="/workspace",
    )
    with pytest.raises(ValueError, match="obbligatorio"):
        PathGuard(env)
