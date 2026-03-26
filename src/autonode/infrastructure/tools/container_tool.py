"""
Container shell tool helpers.
"""

from __future__ import annotations

import subprocess

from langchain_core.tools import BaseTool, tool

from autonode.core.logging import LoggerFactory
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools.path_guard import PathGuard


def docker_exec(
    environment: ExecutionEnvironmentModel,
    command: list[str],
    *,
    env_vars: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    env_args: list[str] = []
    for key, value in (env_vars or {}).items():
        env_args.extend(["-e", f"{key}={value}"])
    return subprocess.run(
        [
            "docker",
            "exec",
            *env_args,
            "-w",
            environment.container_workspace_path,
            environment.sandbox_id,
            *command,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


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
            result = docker_exec(environment, ["sh", "-lc", command], timeout=60)
            return compose_output_and_mirror(
                stdout=result.stdout,
                stderr=result.stderr,
                prefix="[DOCKER_EXEC] > ",
            )
        except subprocess.TimeoutExpired:
            LoggerFactory.get_logger().warning("[DOCKER_EXEC] > timeout (60s) superato.")
            return "ERRORE: timeout (60s) superato."
        except Exception as e:
            LoggerFactory.get_logger().exception("[DOCKER_EXEC] > errore subprocess shell: %s", e)
            return f"ERRORE: {e}"

    return shell
