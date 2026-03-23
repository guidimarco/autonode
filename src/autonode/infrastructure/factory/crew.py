"""
LangChain agent factory: builds runnable agents from config using ChatOpenAI and tool binding.
The system_prompt (if set in config) is prepended to every invocation via a RunnableLambda,
keeping graph nodes free from prompt-management concerns.
"""

import os
from typing import Any

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from autonode.core.agents.models import AgentModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.infrastructure.config.loader import load_agents_config
from autonode.infrastructure.tools.registry import ToolRegistry


class CrewFactory(AgentFactoryPort):
    """Creates LangChain runnable agents from agents config and a tool registry."""

    def __init__(
        self,
        config_path: str = "config/agents.yaml",
        *,
        tool_registry: ToolRegistry,
    ):
        self._config_path = config_path
        # Il catalogo ora è un dizionario di AgentModel (Core)
        self._catalog: dict[str, AgentModel] = load_agents_config(config_path)
        self._tool_registry = tool_registry

    def create_agent(self, agent_id: str) -> Runnable[Any, Any]:
        """
        Build a single agent: [system_prompt prepend →] LLM with bound tools.
        The returned runnable accepts list[BaseMessage] and returns an AIMessage.
        """
        config = self._catalog.get(agent_id)
        if not config:
            raise ValueError(f"Agente '{agent_id}' non trovato nel catalogo.")

        api_key = os.getenv("OPEN_ROUTER_API_KEY")
        llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=SecretStr(api_key) if api_key else None,
            base_url="https://openrouter.ai/api/v1",
        )
        tools = self._tool_registry.get_tool_list(config.tools)
        bound_llm: Runnable[Any, Any] = llm.bind_tools(tools) if tools else llm

        system_prompt = config.system_prompt or ""
        if not system_prompt:
            return bound_llm

        def prepend_system(messages: list[BaseMessage]) -> list[BaseMessage]:
            return [SystemMessage(content=system_prompt), *messages]

        return RunnableLambda(prepend_system) | bound_llm

    def tool_names_for_agent(self, agent_id: str) -> list[str]:
        config = self._catalog.get(agent_id)
        if not config:
            raise ValueError(f"Agente '{agent_id}' non trovato nel catalogo.")
        return list(config.tools)

    def create_all(self) -> dict[str, Runnable[Any, Any]]:
        """Build all agents defined in the catalog."""
        return {aid: self.create_agent(aid) for aid in self._catalog}
