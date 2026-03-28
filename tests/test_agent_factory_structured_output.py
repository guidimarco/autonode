"""LangChainAgentFactory structured output: maps LLM payload to ReviewVerdictModel (Core)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.infrastructure.factory.agent_factory import LangChainAgentFactory
from autonode.infrastructure.factory.review_verdict_schema import ReviewVerdictSchema
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.session_logger import make_test_session_logger


def _minimal_agents_yaml(path: Path) -> str:
    p = path / "agents.yaml"
    p.write_text(
        """
agents:
  - id: reviewer_like
    model: test/model
    tools: []
""".strip() + "\n",
        encoding="utf-8",
    )
    return str(p)


_TEST_SID = "550e8400-e29b-41d4-a716-446655440001"


def _registry(tmp_path: Path) -> ToolRegistry:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = ExecutionEnvironmentModel(
        session_id=_TEST_SID,
        sandbox_id=_TEST_SID,
        repo_host_path=str(repo),
    )
    return ToolRegistry(execution_env=env, session_logger=make_test_session_logger())


def test_create_agent_structured_output_maps_parsed_schema_to_core(tmp_path: Path) -> None:
    agents_path = _minimal_agents_yaml(tmp_path)
    registry = _registry(tmp_path)
    expected_raw = AIMessage(content="raw assistant text")

    with patch("autonode.infrastructure.factory.agent_factory.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _msgs: {
                "raw": expected_raw,
                "parsed": ReviewVerdictSchema(
                    is_approved=True,
                    feedback="LGTM",
                    missing_requirements=["docs"],
                ),
            }
        )

        factory = LangChainAgentFactory(config_path=agents_path, tool_registry=registry)
        runnable = factory.create_agent(
            "reviewer_like",
            structured_output_model=ReviewVerdictModel,
        )
        out = runnable.invoke([HumanMessage(content="please review")])

    assert out["message"] is expected_raw
    assert out["review_verdict"] == ReviewVerdictModel(
        is_approved=True,
        feedback="LGTM",
        missing_requirements=["docs"],
    )
    mock_llm.with_structured_output.assert_called_once()


def test_create_agent_structured_output_accepts_parsed_as_dict(tmp_path: Path) -> None:
    """LangChain may surface parsed as a plain dict; model_validate must still yield Core."""
    agents_path = _minimal_agents_yaml(tmp_path)
    registry = _registry(tmp_path)

    with patch("autonode.infrastructure.factory.agent_factory.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _msgs: {
                "raw": AIMessage(content="x"),
                "parsed": {
                    "is_approved": False,
                    "feedback": "fix tests",
                    "missing_requirements": ["unit tests"],
                },
            }
        )

        factory = LangChainAgentFactory(config_path=agents_path, tool_registry=registry)
        runnable = factory.create_agent(
            "reviewer_like",
            structured_output_model=ReviewVerdictModel,
        )
        out = runnable.invoke([HumanMessage(content="rev")])

    assert out["review_verdict"] == ReviewVerdictModel(
        is_approved=False,
        feedback="fix tests",
        missing_requirements=["unit tests"],
    )


def test_create_agent_structured_invalid_parsed_falls_back(tmp_path: Path) -> None:
    """Pydantic validation failure on `parsed` yields safe Core fallback."""
    agents_path = _minimal_agents_yaml(tmp_path)
    registry = _registry(tmp_path)

    with patch("autonode.infrastructure.factory.agent_factory.ChatOpenAI") as mock_cls:
        mock_llm = MagicMock()
        mock_cls.return_value = mock_llm
        mock_llm.with_structured_output.return_value = RunnableLambda(
            lambda _msgs: {
                "raw": AIMessage(content="x"),
                "parsed": {"is_approved": "not-a-bool", "feedback": 123},
            }
        )

        factory = LangChainAgentFactory(config_path=agents_path, tool_registry=registry)
        runnable = factory.create_agent(
            "reviewer_like",
            structured_output_model=ReviewVerdictModel,
        )
        out = runnable.invoke([HumanMessage(content="rev")])

    assert out["review_verdict"] == ReviewVerdictModel(
        is_approved=False,
        feedback="Output strutturato reviewer non valido (fallback).",
        missing_requirements=[],
    )


def test_create_agent_rejects_unknown_structured_model(tmp_path: Path) -> None:
    agents_path = _minimal_agents_yaml(tmp_path)
    registry = _registry(tmp_path)

    factory = LangChainAgentFactory(config_path=agents_path, tool_registry=registry)
    with pytest.raises(ValueError, match="Structured output non supportato"):
        factory.create_agent("reviewer_like", structured_output_model=int)
