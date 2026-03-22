"""Stub di AgentFactoryPort per test di compilazione grafo senza LLM."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from autonode.core.agents.ports import AgentFactoryPort


class StubAgentFactory(AgentFactoryPort):
    """Allinea i tool ai nodi `alpha_agent` / `beta_agent` dei fixture di test."""

    def create_agent(self, agent_id: str) -> Any:
        class _Runnable:
            def invoke(self, _messages: object) -> AIMessage:
                return AIMessage(content="OK")

        return _Runnable()

    def tool_names_for_agent(self, agent_id: str) -> list[str]:
        if agent_id == "alpha_agent":
            return ["read_file", "shell"]
        if agent_id == "beta_agent":
            return ["read_file", "list_directory"]
        return []

    def create_all(self) -> dict[str, Any]:
        return {}
