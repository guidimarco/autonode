"""ToolRegistry: mandatory Docker-class sandbox (no host-runtime)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools.registry import ToolRegistry, resolve_aider_model


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
