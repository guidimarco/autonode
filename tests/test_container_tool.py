"""docker_exec via Docker SDK (mocked)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.logging.stderr_adapter import StandardErrorAutonodeLogger
from autonode.infrastructure.tools.container_tool import compose_output_and_mirror, docker_exec
from tests.stubs.session_logger import make_test_session_logger


@pytest.fixture
def exec_env() -> ExecutionEnvironmentModel:
    return ExecutionEnvironmentModel(
        session_id="s1",
        sandbox_id="cid",
        repo_host_path="/repo",
    )


def test_docker_exec_uses_bash_workdir_and_demux(exec_env: ExecutionEnvironmentModel) -> None:
    mock_container = MagicMock()
    mock_container.exec_run.return_value = (0, (b"out\n", b"err\n"))
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container

    with patch(
        "autonode.infrastructure.tools.container_tool.docker.from_env", return_value=mock_client
    ):
        r = docker_exec(
            exec_env,
            ["/bin/bash", "-lc", "echo hi"],
            session_logger=make_test_session_logger(),
        )

    mock_client.containers.get.assert_called_once_with("cid")
    mock_container.exec_run.assert_called_once()
    kw = mock_container.exec_run.call_args.kwargs
    assert kw["cmd"] == ["/bin/bash", "-lc", "echo hi"]
    assert kw["workdir"] == "/workspace"
    assert kw["demux"] is True
    assert r.stdout == "out\n"
    assert r.stderr == "err\n"
    assert r.exit_code == 0


def test_compose_output_and_mirror_logs_no_output_line_with_exit_code() -> None:
    captured: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record.getMessage())

    py = logging.getLogger("test.container_tool.compose")
    py.handlers.clear()
    py.setLevel(logging.INFO)
    py.addHandler(_Capture())
    logger = StandardErrorAutonodeLogger(py)
    out = compose_output_and_mirror(
        session_logger=logger,
        stdout="",
        stderr="",
        prefix="[DOCKER_EXEC] > ",
        exit_code=0,
    )
    assert out == "(nessun output)"
    assert any("Comando completato (exit code: 0, no output)" in line for line in captured)
