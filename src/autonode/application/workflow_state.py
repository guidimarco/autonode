"""
LangGraph shared state for configuration-driven workflows.

Designed for checkpointers: keep serializable-friendly values in context/artifacts;
messages use LangGraph's add_messages reducer.
"""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages


def _merge_shallow(left: dict[str, Any], right: dict[str, Any] | None) -> dict[str, Any]:
    if right is None:
        return left
    return {**left, **right}


class GraphWorkflowState(TypedDict):
    """Extensible workflow state (short-term / thread memory via checkpointer)."""

    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int
    verdict: str
    context: Annotated[dict[str, Any], _merge_shallow]
    artifacts: Annotated[dict[str, Any], _merge_shallow]
    status: NotRequired[str]
    current_node: NotRequired[str]
    last_router_decision: NotRequired[str]


def make_initial_graph_state(
    prompt: str,
    *,
    context: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
) -> GraphWorkflowState:
    """Build initial state for invoke/stream with thread_id in config."""
    return GraphWorkflowState(
        messages=[HumanMessage(content=prompt)],
        iteration=0,
        verdict="",
        context=context or {},
        artifacts=artifacts or {},
    )
