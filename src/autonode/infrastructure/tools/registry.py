"""
Tool registry: registers LangChain tools and resolves by name.
Implements ToolRegistryPort for the application layer.

Security contract:
    Tutti i tool file/shell operano sotto ``execution_env.worktree_host_path`` (bind nel container).
    Path traversal viene bloccato prima di I/O o subprocess.
"""

import os
import subprocess
from pathlib import Path

from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import BaseTool, tool

from autonode.core.logging import LoggerFactory
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.tools.codebase_search import make_search_codebase_tool
from autonode.infrastructure.tools.path_guard import PathGuard
from autonode.infrastructure.tools.repository_map import make_get_repository_map_tool

_DEFAULT_AIDER_MODEL = "openrouter/mistralai/devstral-2512"


def resolve_aider_model() -> str:
    """Model id passed to Aider's ``--model`` (env ``AIDER_MODEL`` or default)."""
    v = os.getenv("AIDER_MODEL", "").strip()
    return v or _DEFAULT_AIDER_MODEL


def _docker_exec(
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


def _compose_output_and_mirror(
    *,
    stdout: str,
    stderr: str,
    prefix: str,
) -> str:
    """
    In an MCP (Model Context Protocol) architecture, 'stdout' (FD 1) is reserved
    exclusively for JSON-RPC communication between the server and the client.
    Any raw text printed to stdout would corrupt the protocol and crash the session.

    This function implements a 'Double Stream' strategy:
    1. FUNCTIONAL FLOW (to Agent): Both stdout and stderr from the subprocess
       are bundled into a single string and returned to the LLM so it can
       understand the outcome of its action.
    2. DIAGNOSTIC FLOW (to Human): The same content is mirrored to 'stderr' (FD 2)
       via the LoggerFactory. Since MCP clients (like Claude or the Inspector)
       ignore stderr for protocol data but display it in their logs, this allows
       real-time human monitoring without breaking the machine-to-machine link.
    """
    if stdout:
        _log_stream_lines(prefix, stdout)
    output = stdout
    if stderr:
        _log_stream_lines(f"{prefix}[stderr] ", stderr)
        output += f"\n[stderr]\n{stderr}"
    return output or "(nessun output)"


def _make_container_shell_tool(
    environment: ExecutionEnvironmentModel,
    path_guard: PathGuard,
) -> BaseTool:
    @tool
    def shell(command: str) -> str:
        """
        Esegui un comando shell nella sandbox Docker della sessione.
        """
        try:
            path_guard.validate_shell_command(command)
        except ValueError as e:
            return f"ERRORE: {e}"

        try:
            result = _docker_exec(environment, ["sh", "-lc", command], timeout=60)
            return _compose_output_and_mirror(
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


def _make_container_aider_tool(
    environment: ExecutionEnvironmentModel,
    path_guard: PathGuard,
) -> BaseTool:
    @tool
    def aider(instruction: str, files: list[str]) -> str:
        """
        Usa Aider nel container Docker della sessione.
        """
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
            result = _docker_exec(environment, command, env_vars=env_vars)
            return _compose_output_and_mirror(
                stdout=result.stdout,
                stderr=result.stderr,
                prefix="[AIDER] > ",
            )
        except Exception as e:
            LoggerFactory.get_logger().exception("[AIDER] > errore subprocess aider: %s", e)
            return f"Aider: {e}"

    return aider


class ToolRegistry(ToolRegistryPort):
    """Registry of tools by name. Used by agent factory and workflow to resolve tools."""

    def __init__(self, *, execution_env: ExecutionEnvironmentModel) -> None:
        if execution_env.sandbox_id == "host-runtime":
            raise ValueError(
                "Esecuzione su host disabilitata: usare DockerAdapter "
                "(sandbox_id != 'host-runtime')."
            )
        self._execution_env = execution_env
        self._path_guard = PathGuard(execution_env)
        self._tools: dict[str, BaseTool] = {}
        self._load_standard_tools()

    def _load_standard_tools(self) -> None:
        self.register(
            "aider",
            _make_container_aider_tool(self._execution_env, self._path_guard),
        )

        # Read-only exploration (scoped to root_dir)
        self.register(
            "get_repository_map", make_get_repository_map_tool(self._path_guard.host_root)
        )
        self.register("search_codebase", make_search_codebase_tool(self._path_guard.host_root))

        # File I/O — restricted to root_dir by FileManagementToolkit
        file_toolkit = FileManagementToolkit(
            root_dir=self._path_guard.host_root,
            selected_tools=["read_file", "write_file", "list_directory", "move_file", "copy_file"],
        ).get_tools()
        for t in file_toolkit:
            self.register(t.name, t)

        self.register(
            "shell",
            _make_container_shell_tool(self._execution_env, self._path_guard),
        )

    def bind_execution_environment(
        self,
        execution_env: ExecutionEnvironmentModel | None,
    ) -> "ToolRegistry":
        if execution_env is None:
            raise ValueError(
                "bind_execution_environment richiede execution_env; "
                "nessun fallback sull'host è consentito."
            )
        return ToolRegistry(execution_env=execution_env)

    def register(self, name: str, tool_obj: BaseTool) -> None:
        self._tools[name] = tool_obj

    def get_tool_list(self, names: list[str]) -> list[BaseTool]:
        return [self._tools[n] for n in names if n in self._tools]

    def get_tool_list_strict(self, names: list[str]) -> list[BaseTool]:
        missing = [n for n in names if n not in self._tools]
        if missing:
            raise ValueError(f"Tool non registrati: {missing}")
        return [self._tools[n] for n in names]

    def list_available_tools(self) -> list[str]:
        return list(self._tools.keys())
