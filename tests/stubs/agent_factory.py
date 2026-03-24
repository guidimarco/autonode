"""Stub di AgentFactoryPort per test di compilazione grafo senza LLM."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort


class StubAgentFactory(AgentFactoryPort):
    """Allinea i tool ai nodi `alpha_agent` / `beta_agent` dei fixture di test."""

    def __init__(
        self,
        *,
        structured_review_verdict: ReviewVerdictModel | None = None,
    ) -> None:
        self._structured_review_verdict = structured_review_verdict or ReviewVerdictModel(
            is_approved=False,
            feedback="",
            missing_requirements=[],
        )

    def create_agent(
        self,
        agent_id: str,
        *,
        structured_output_model: type[Any] | None = None,
    ) -> Any:
        use_structured = structured_output_model is ReviewVerdictModel
        verdict = self._structured_review_verdict

        class _Runnable:
            def invoke(self, _messages: object) -> Any:
                if use_structured:
                    return {
                        "message": AIMessage(content="stub structured reviewer", tool_calls=[]),
                        "review_verdict": verdict,
                    }
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
