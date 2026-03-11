"""
LangChain agent factory: builds runnable agents from config using ChatOpenAI and tool binding.
"""

import os
from typing import Any, cast

from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from autonode.infrastructure.config_loader import load_agents_config
from autonode.infrastructure.tools.registry import ToolRegistry


class CrewFactory:
    """Creates LangChain runnable agents from agents config and a tool registry."""

    def __init__(
        self,
        config_path: str = "config/agents.yaml",
        tool_registry: ToolRegistry | None = None,
    ):
        self._config_path = config_path
        self._catalog = load_agents_config(config_path)
        self._tool_registry = tool_registry or ToolRegistry()

    def create_agent(self, agent_id: str) -> RunnableSerializable[Any, Any]:
        """Build a single agent (LLM + bound tools)."""
        config = self._catalog.get(agent_id)
        if not config:
            raise ValueError(f"Agente {agent_id} non trovato nel catalogo.")
        llm = ChatOpenAI(
            model=config["model"],
            temperature=config.get("temperature", 0.0),
            api_key=lambda: os.getenv("OPEN_ROUTER_API_KEY") or "",
            base_url="https://openrouter.ai/api/v1",
        )
        tool_names = config.get("tools", [])
        tools = self._tool_registry.get_tool_list(tool_names)
        return cast(RunnableSerializable[Any, Any], llm.bind_tools(tools))

    def create_all(self) -> dict[str, RunnableSerializable[Any, Any]]:
        """Build all agents from the catalog."""
        return {aid: self.create_agent(aid) for aid in self._catalog}
