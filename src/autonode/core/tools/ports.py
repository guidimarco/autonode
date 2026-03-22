"""
Abstract ports (interfaces) for tools.
"""

from abc import ABC, abstractmethod
from typing import Any


class ToolPort(ABC):
    """Abstract interface for a tool that can be invoked by an agent."""

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def invoke(self, args: dict[str, Any]) -> Any:
        pass


class ToolRegistryPort(ABC):
    """Abstract interface for resolving tools by name."""

    @abstractmethod
    def get_tool_list(self, names: list[str]) -> list[Any]:
        pass

    @abstractmethod
    def get_tool_list_strict(self, names: list[str]) -> list[Any]:
        """Like get_tool_list but raises if any name is missing from the registry."""

    @abstractmethod
    def list_available_tools(self) -> list[str]:
        pass
