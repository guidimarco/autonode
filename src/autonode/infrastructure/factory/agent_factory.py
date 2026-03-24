"""
LangChain agent factory: runnable agents from config (ChatOpenAI + tool binding).
Optional system_prompt is prepended per invocation via RunnableLambda.
"""

from __future__ import annotations

import os
from typing import Any, cast

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError

from autonode.core.agents.models import AgentModel, ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.infrastructure.config.loader import load_agents_config
from autonode.infrastructure.factory.review_verdict_schema import ReviewVerdictSchema
from autonode.infrastructure.tools.registry import ToolRegistry


def _map_structured_include_raw(out: Any) -> dict[str, Any]:
    """Normalize LangChain `include_raw=True` payload to core verdict + raw message."""
    if not isinstance(out, dict):
        msg = f"Structured output atteso come dict (include_raw=True), ottenuto {type(out)!r}"
        raise TypeError(msg)
    raw_msg = out.get("raw")
    parsed = out.get("parsed")
    if isinstance(parsed, ReviewVerdictSchema):
        verdict = parsed.to_core()
    elif parsed is None:
        verdict = ReviewVerdictModel(
            is_approved=False,
            feedback="",
            missing_requirements=[],
        )
    else:
        try:
            verdict = ReviewVerdictSchema.model_validate(parsed).to_core()
        except (ValidationError, ValueError, TypeError):
            verdict = ReviewVerdictModel(
                is_approved=False,
                feedback="Output strutturato reviewer non valido (fallback).",
                missing_requirements=[],
            )
    return {"message": raw_msg, "review_verdict": verdict}


class LangChainAgentFactory(AgentFactoryPort):
    """Builds LangChain runnable agents from agents config and a tool registry."""

    def __init__(
        self,
        config_path: str = "config/agents.yaml",
        *,
        tool_registry: ToolRegistry,
    ):
        self._config_path = config_path
        self._catalog: dict[str, AgentModel] = load_agents_config(config_path)
        self._tool_registry = tool_registry

    def create_agent(
        self,
        agent_id: str,
        *,
        structured_output_model: type[Any] | None = None,
    ) -> Runnable[Any, Any]:
        config = self._catalog.get(agent_id)
        if not config:
            raise ValueError(f"Agente '{agent_id}' non trovato nel catalogo.")

        if structured_output_model is not None:
            if structured_output_model is not ReviewVerdictModel:
                raise ValueError(
                    f"Structured output non supportato per {structured_output_model!r}; "
                    "usare ReviewVerdictModel."
                )

        api_key = os.getenv("OPEN_ROUTER_API_KEY")
        llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=SecretStr(api_key) if api_key else None,
            base_url="https://openrouter.ai/api/v1",
        )
        tools = self._tool_registry.get_tool_list(config.tools)
        bound_llm: Runnable[Any, Any] = llm.bind_tools(tools) if tools else llm

        tail: Runnable[Any, Any]
        if structured_output_model is not None:
            structured_runnable = cast(Any, bound_llm).with_structured_output(
                ReviewVerdictSchema,
                include_raw=True,
            )
            tail = structured_runnable | RunnableLambda(_map_structured_include_raw)
        else:
            tail = bound_llm

        system_prompt = config.system_prompt or ""
        if not system_prompt:
            return tail

        def prepend_system(messages: list[BaseMessage]) -> list[BaseMessage]:
            return [SystemMessage(content=system_prompt), *messages]

        return RunnableLambda(prepend_system) | tail

    def tool_names_for_agent(self, agent_id: str) -> list[str]:
        config = self._catalog.get(agent_id)
        if not config:
            raise ValueError(f"Agente '{agent_id}' non trovato nel catalogo.")
        return list(config.tools)

    def create_all(self) -> dict[str, Runnable[Any, Any]]:
        return {aid: self.create_agent(aid) for aid in self._catalog}
