"""
Container shell tool helpers.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import cast

from docker.client import DockerClient
from langchain_core.tools import BaseTool, tool

import docker
from autonode.core.logging import LoggerFactory
from autonode.core.sandbox.models import (
    CONTAINER_WORKSPACE_PATH,
    ExecutionEnvironmentModel,
)
from autonode.infrastructure.tools.path_guard import PathGuard


@dataclass(frozen=True, slots=True)
class DockerExecResult:
    stdout: str
    stderr: str
    exit_code: int


def docker_exec(
    environment: ExecutionEnvironmentModel,
    command: list[str],
    *,
    env_vars: dict[str, str] | None = None,
    timeout: int | None = None,
) -> DockerExecResult:
    client: DockerClient = docker.from_env()  # type: ignore[attr-defined]
    container = client.containers.get(environment.sandbox_id)
    effective_timeout = 60 if timeout is None else timeout

    def _run() -> tuple[int, tuple[bytes, bytes] | None]:
        return cast(
            tuple[int, tuple[bytes, bytes] | None],
            container.exec_run(
                cmd=command,
                workdir=CONTAINER_WORKSPACE_PATH,
                environment=env_vars or {},
                demux=True,
            ),
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            exit_code, streams = future.result(timeout=effective_timeout)
        except FutureTimeout:
            LoggerFactory.get_logger().warning(
                "[DOCKER_EXEC] > timeout (%ss) superato.",
                effective_timeout,
            )
            raise TimeoutError(f"timeout ({effective_timeout}s) superato") from None

    if streams is None:
        stdout_b, stderr_b = b"", b""
    else:
        stdout_b, stderr_b = streams
    stdout = (stdout_b or b"").decode(errors="replace")
    stderr = (stderr_b or b"").decode(errors="replace")
    return DockerExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


def _log_stream_lines(prefix: str, content: str) -> None:
    logger = LoggerFactory.get_logger()
    for line in content.splitlines():
        logger.info("%s%s", prefix, line)


def compose_output_and_mirror(*, stdout: str, stderr: str, prefix: str) -> str:
    if stdout:
        _log_stream_lines(prefix, stdout)
    output = stdout
    if stderr:
        _log_stream_lines(f"{prefix}[stderr] ", stderr)
        output += f"\n[stderr]\n{stderr}"
    return output or "(nessun output)"


def make_container_shell_tool(
    environment: ExecutionEnvironmentModel,
    path_guard: PathGuard,
) -> BaseTool:
    @tool
    def shell(command: str) -> str:
        """Esegui un comando shell nella sandbox Docker della sessione."""
        try:
            path_guard.validate_shell_command(command)
        except ValueError as e:
            return f"ERRORE: {e}"

        try:
            result = docker_exec(
                environment,
                ["/bin/bash", "-lc", command],
                timeout=60,
            )
            return compose_output_and_mirror(
                stdout=result.stdout,
                stderr=result.stderr,
                prefix="[DOCKER_EXEC] > ",
            )
        except TimeoutError:
            return "ERRORE: timeout (60s) superato."
        except Exception as e:
            LoggerFactory.get_logger().exception("[DOCKER_EXEC] > errore exec shell: %s", e)
            return f"ERRORE: {e}"

    return shell
