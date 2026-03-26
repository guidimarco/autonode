"""Tool registry: thin wiring layer for infrastructure tools."""

from langchain_core.tools import BaseTool

from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.tools.aider_tool import make_container_aider_tool
from autonode.infrastructure.tools.container_tool import make_container_shell_tool
from autonode.infrastructure.tools.file_tool import make_file_tools
from autonode.infrastructure.tools.git_tool import make_git_diff_tool
from autonode.infrastructure.tools.path_guard import PathGuard
from autonode.infrastructure.tools.repository_map import make_get_repository_map_tool
from autonode.infrastructure.tools.search_tool import make_search_codebase_tool


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
            make_container_aider_tool(self._execution_env, self._path_guard),
        )
        self.register(
            "get_repository_map", make_get_repository_map_tool(self._path_guard.host_root)
        )
        self.register("search_codebase", make_search_codebase_tool(self._path_guard.host_root))
        self.register("git_diff", make_git_diff_tool(self._path_guard.host_root))
        for t in make_file_tools(self._path_guard.host_root):
            self.register(t.name, t)
        self.register(
            "shell",
            make_container_shell_tool(self._execution_env, self._path_guard),
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
