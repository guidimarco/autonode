"""
Aider container tool helpers.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from autonode.core.logging import LoggerFactory
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.tools.container_tool import compose_output_and_mirror, docker_exec
from autonode.infrastructure.tools.path_guard import PathGuard

_DEFAULT_AIDER_MODEL = "openrouter/mistralai/devstral-2512"


def resolve_aider_model() -> str:
    """Model id passed to Aider's ``--model`` (env ``AIDER_MODEL`` or default)."""
    v = os.getenv("AIDER_MODEL", "").strip()
    return v or _DEFAULT_AIDER_MODEL


def make_container_aider_tool(
    environment: ExecutionEnvironmentModel,
    path_guard: PathGuard,
) -> BaseTool:
    @tool
    def aider(instruction: str, files: list[str]) -> str:
        """Usa Aider nel container Docker della sessione."""
        normalized_files: list[str] = []
        for relative_path in files:
            try:
                candidate = path_guard.resolve_relative_path(relative_path)
            except ValueError as e:
                return f"ERRORE: path file non valido '{relative_path}': {e}"
            if not candidate.exists() or not candidate.is_file():
                return f"ERRORE: file inesistente per Aider: '{relative_path}'"
            normalized_files.append(
                str(candidate.relative_to(Path(path_guard.host_root))),
            )

        command = [
            "aider",
            "--model",
            resolve_aider_model(),
            "--yes",
            "--no-git",
            "--no-auto-commit",
            "--cache-prompts",
            "--no-stream",
            "--message",
            instruction,
            "--api-key",
            f"openrouter={os.getenv('OPEN_ROUTER_API_KEY')}",
            *normalized_files,
        ]
        try:
            env_vars = {}
            api_key = os.getenv("OPEN_ROUTER_API_KEY")
            if api_key:
                env_vars["OPEN_ROUTER_API_KEY"] = api_key
            result = docker_exec(environment, command, env_vars=env_vars)
            return compose_output_and_mirror(
                stdout=result.stdout,
                stderr=result.stderr,
                prefix="[AIDER] > ",
            )
        except Exception as e:
            LoggerFactory.get_logger().exception("[AIDER] > errore subprocess aider: %s", e)
            return f"Aider: {e}"

    return aider
