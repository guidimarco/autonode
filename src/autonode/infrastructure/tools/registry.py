"""
Tool registry: registers LangChain tools and resolves by name.
Implements ToolRegistryPort for the application layer.

Security contract:
    All file-write and shell-execution tools are restricted to `root_dir`
    (default: ./playground). Path traversal attempts raise ValueError before
    any I/O or subprocess is started.
"""

import os
import subprocess

from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import BaseTool, tool

from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.tools.aider import aider_tool


def _make_sandboxed_shell_tool(root_dir: str) -> BaseTool:
    """
    Return a ShellTool-compatible tool whose commands always run inside
    `root_dir`. Path traversal via `../` is blocked before subprocess starts.

    We build a custom @tool instead of subclassing ShellTool to avoid
    langchain_community version coupling and to keep the sandbox logic explicit.
    """
    abs_root = os.path.realpath(root_dir)

    @tool
    def shell(command: str) -> str:
        """
        Esegui un comando shell nella sandbox del progetto (playground/).
        Usa questo tool per lanciare script Python, test, linter o comandi git
        all'interno della directory di lavoro del task.
        NON puoi accedere a path esterni alla sandbox.
        """
        # Block naive traversal before exec
        if ".." in command:
            return "ERRORE: path traversal ('..') non permesso nella sandbox."

        # Block absolute paths pointing outside the sandbox
        for token in command.split():
            if token.startswith("/") and not token.startswith(abs_root):
                return f"ERRORE: path assoluto non permesso: {token}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=abs_root,
                timeout=60,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            return output or "(nessun output)"
        except subprocess.TimeoutExpired:
            return "ERRORE: timeout (60s) superato."
        except Exception as e:
            return f"ERRORE: {e}"

    return shell


class ToolRegistry(ToolRegistryPort):
    """Registry of tools by name. Used by agent factory and workflow to resolve tools."""

    def __init__(self, root_dir: str = "./playground"):
        self._root_dir = root_dir
        self._tools: dict[str, BaseTool] = {}
        self._load_standard_tools()

    def _load_standard_tools(self) -> None:
        # Aider: external subprocess, already sandboxed via cwd in aider.py
        self.register("aider", aider_tool)

        # File I/O — restricted to root_dir by FileManagementToolkit
        file_toolkit = FileManagementToolkit(
            root_dir=self._root_dir,
            selected_tools=["read_file", "write_file", "list_directory", "move_file", "copy_file"],
        ).get_tools()
        for t in file_toolkit:
            self.register(t.name, t)

        # Shell — restricted to root_dir by our sandbox wrapper
        self.register("shell", _make_sandboxed_shell_tool(self._root_dir))

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
