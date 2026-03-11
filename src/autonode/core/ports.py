"""
Abstract ports (interfaces) for infrastructure. Enables swapping LangChain
for another runtime (e.g. Semantic Kernel) without changing application layer.
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
    def list_available_tools(self) -> list[str]:
        pass


class AgentFactoryPort(ABC):
    """Abstract interface for creating runnable agents from config."""

    @abstractmethod
    def create_agent(self, agent_id: str) -> Any:
        pass

    @abstractmethod
    def create_all(self) -> dict[str, Any]:
        pass
