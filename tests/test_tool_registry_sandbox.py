"""ToolRegistry: mandatory Docker-class sandbox (no host-runtime)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.core.logging import LoggerFactory
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools import registry as registry_module
from autonode.infrastructure.tools.registry import ToolRegistry, resolve_aider_model


class _SpyLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)

    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)

    def warning(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)

    def error(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)

    def critical(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)

    def exception(self, msg: str, *args: object, **kwargs: object) -> None:
        self.messages.append(msg % args if args else msg)


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


def test_compose_output_and_mirror_keeps_output_and_logs_lines() -> None:
    spy = _SpyLogger()
    LoggerFactory.set_logger(spy)
    try:
        output = registry_module._compose_output_and_mirror(
            stdout="line-a\nline-b\n",
            stderr="err-a\n",
            prefix="[DOCKER_EXEC] > ",
        )

        assert output == "line-a\nline-b\n\n[stderr]\nerr-a\n"
        assert spy.messages == [
            "[DOCKER_EXEC] > line-a",
            "[DOCKER_EXEC] > line-b",
            "[DOCKER_EXEC] > [stderr] err-a",
        ]
    finally:
        LoggerFactory.reset_to_default()
