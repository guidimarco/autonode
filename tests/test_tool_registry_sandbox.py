"""ToolRegistry: mandatory Docker-class sandbox (no host-runtime)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools.aider_tool import resolve_aider_model
from autonode.infrastructure.tools.registry import ToolRegistry


def test_resolve_aider_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIDER_MODEL", "openrouter/custom/model")
    assert resolve_aider_model() == "openrouter/custom/model"


def test_resolve_aider_model_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIDER_MODEL", raising=False)
    assert resolve_aider_model() == "openrouter/mistralai/devstral-2512"


def test_tool_registry_rejects_host_runtime(tmp_path: Path) -> None:
    env = ExecutionEnvironmentModel(
        session_id="s",
        sandbox_id="host-runtime",
        worktree_host_path=str(tmp_path),
        container_workspace_path=str(tmp_path),
    )
    with pytest.raises(ValueError, match="host"):
        ToolRegistry(execution_env=env)


def test_registry_exposes_expected_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_container_shell_tool",
        lambda *_a, **_k: MagicMock(name="shell"),
    )
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_container_aider_tool",
        lambda *_a, **_k: MagicMock(name="aider"),
    )
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_search_codebase_tool",
        lambda *_a, **_k: MagicMock(name="search_codebase"),
    )
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_get_repository_map_tool",
        lambda *_a, **_k: MagicMock(name="get_repository_map"),
    )
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_git_diff_tool",
        lambda *_a, **_k: MagicMock(name="git_diff"),
    )
    monkeypatch.setattr(
        "autonode.infrastructure.tools.registry.make_file_tools",
        lambda *_a, **_k: [],
    )

    env = ExecutionEnvironmentModel(
        session_id="s",
        sandbox_id="sandbox-1",
        worktree_host_path=str(tmp_path),
        container_workspace_path="/workspace",
    )
    registry = ToolRegistry(execution_env=env)
    available = registry.list_available_tools()
    assert "shell" in available
    assert "aider" in available
    assert "search_codebase" in available
    assert "get_repository_map" in available
    assert "git_diff" in available
