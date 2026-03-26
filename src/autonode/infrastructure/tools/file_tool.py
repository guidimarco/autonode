"""
Minimal file-management tool wiring.
"""

from __future__ import annotations

from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import BaseTool


def make_file_tools(root_dir: str) -> list[BaseTool]:
    """Return essential file tools for the current workflow."""
    return FileManagementToolkit(
        root_dir=root_dir,
        selected_tools=["read_file", "write_file", "list_directory"],
    ).get_tools()
