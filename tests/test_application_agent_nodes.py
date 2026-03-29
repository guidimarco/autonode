"""Unit tests for application.agents.nodes helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from autonode.application.agents.nodes import resolve_tool_names, to_message
from autonode.application.workflow.factories.registry import FactoryContext


def test_to_message_passes_through_base_message() -> None:
    msg = AIMessage(content="x")
    assert to_message(msg) is msg


def test_to_message_wraps_non_message() -> None:
    out = to_message(42)
    assert isinstance(out, AIMessage)
    assert out.content == "42"


def test_resolve_tool_names_merges_and_dedupes() -> None:
    wf = MagicMock()
    agent_factory = MagicMock()
    agent_factory.tool_names_for_agent.return_value = ["a", "b"]
    registry = MagicMock()
    vcs = MagicMock()
    ctx = FactoryContext(
        workflow=wf,
        agent_factory=agent_factory,
        tool_registry=registry,
        vcs_provider=vcs,
    )
    assert resolve_tool_names(ctx, "aid", ["b", "c"]) == ["a", "b", "c"]
