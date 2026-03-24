"""
Abstract ports (interfaces) for agents.
"""

from abc import ABC, abstractmethod
from typing import Any


class AgentFactoryPort(ABC):
    """Abstract interface for creating runnable agents from config."""

    @abstractmethod
    def create_agent(
        self,
        agent_id: str,
        *,
        structured_output_model: type[Any] | None = None,
    ) -> Any:
        pass

    @abstractmethod
    def tool_names_for_agent(self, agent_id: str) -> list[str]:
        """Tool ids from agent registry config (for ToolNode wiring)."""

    @abstractmethod
    def create_all(self) -> dict[str, Any]:
        pass
