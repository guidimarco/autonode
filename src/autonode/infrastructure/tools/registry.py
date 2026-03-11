"""
Tool registry: registers LangChain tools and resolves by name.
Implements ToolRegistryPort for the application layer.
"""

from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import BaseTool

from autonode.infrastructure.tools.aider import aider_tool


class ToolRegistry:
    """Registry of tools by name. Used by agent factory and workflow to resolve tools."""

    def __init__(self, root_dir: str = "./playground"):
        self._root_dir = root_dir
        self._tools: dict[str, BaseTool] = {}
        self._load_standard_tools()

    def _load_standard_tools(self) -> None:
        self.register("aider", aider_tool)

        file_toolkit = FileManagementToolkit(
            root_dir=self._root_dir,
            selected_tools=["read_file", "list_directory", "write_file"],
        ).get_tools()
        for tool in file_toolkit:
            self.register(tool.name, tool)

    def register(self, name: str, tool_obj: BaseTool) -> None:
        self._tools[name] = tool_obj

    def get_tool_list(self, names: list[str]) -> list[BaseTool]:
        return [self._tools[n] for n in names if n in self._tools]

    def list_available_tools(self) -> list[str]:
        return list(self._tools.keys())
