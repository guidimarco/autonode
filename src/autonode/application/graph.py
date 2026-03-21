"""
LangGraph workflow: coder → reviewer with feedback cycle.

State flow:
    START
      │
      ▼
    coder ──(tool calls?)──► coder_tools ──► coder
      │ (no tools)
      ▼
    reviewer ──(tool calls?)──► reviewer_tools ──► reviewer
      │ (no tools)
      ├─ approved / max iterations ──► END
      └─ needs revision ──► prepare_revision ──► coder

Checkpointing: MemorySaver by default (swap for SqliteSaver for persistence).
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from autonode.core.ports import AgentFactoryPort, ToolRegistryPort

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3


class WorkflowState(TypedDict):
    """Immutable-by-convention state passed between graph nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int
    verdict: str
    # ^ ^ ^ 'approved' | 'needs_revision' | '' (not yet reviewed)


def build_graph(
    factory: AgentFactoryPort,
    registry: ToolRegistryPort,
    checkpointer: Any = None,
) -> Any:
    """
    Compile and return the coder→reviewer StateGraph.

    Args:
        factory:      AgentFactoryPort implementation (e.g. CrewFactory).
        registry:     ToolRegistryPort implementation (e.g. ToolRegistry).
        checkpointer: LangGraph checkpointer; defaults to MemorySaver (in-memory).
                      Pass a SqliteSaver for durable persistence.

    Returns:
        A compiled LangGraph runnable. Invoke with:
            graph.invoke(
                {"messages": [HumanMessage(content=prompt)], "iteration": 0, "verdict": ""},
                config={"configurable": {"thread_id": "<task-id>"}},
            )
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    coder_agent = factory.create_agent("coder")
    reviewer_agent = factory.create_agent("reviewer")
    all_tools = registry.get_tool_list(registry.list_available_tools())

    # ── Node definitions ──────────────────────────────────────────────────────

    def coder_node(state: WorkflowState) -> dict[str, Any]:
        logger.info("[coder] iteration=%d  messages=%d", state["iteration"], len(state["messages"]))
        response = coder_agent.invoke(state["messages"])
        return {"messages": [response]}

    def reviewer_node(state: WorkflowState) -> dict[str, Any]:
        n_messages = len(state["messages"])
        logger.info("[reviewer] iteration=%d  messages=%d", state["iteration"], n_messages)
        response = reviewer_agent.invoke(state["messages"])
        content = response.content if isinstance(response.content, str) else ""
        verdict = "approved" if "APPROVED" in content.upper() else "needs_revision"
        logger.info("[reviewer] verdict=%s", verdict)
        return {"messages": [response], "verdict": verdict}

    def prepare_revision_node(state: WorkflowState) -> dict[str, Any]:
        """Reset verdict and increment counter before sending back to coder."""
        new_iter = state["iteration"] + 1
        logger.info("[prepare_revision] iteration %d → %d", state["iteration"], new_iter)
        return {"iteration": new_iter, "verdict": ""}

    # ── Routing functions ─────────────────────────────────────────────────────

    def route_from_coder(state: WorkflowState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "coder_tools"
        return "reviewer"

    def route_from_reviewer(state: WorkflowState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "reviewer_tools"
        if state["verdict"] == "approved" or state["iteration"] >= MAX_ITERATIONS:
            logger.info(
                "[graph] done | verdict=%s | iteration=%d",
                state["verdict"],
                state["iteration"],
            )
            return END
        return "prepare_revision"

    # ── Graph assembly ────────────────────────────────────────────────────────

    builder = StateGraph(WorkflowState)

    builder.add_node("coder", coder_node)
    builder.add_node("coder_tools", ToolNode(all_tools))
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("reviewer_tools", ToolNode(all_tools))
    builder.add_node("prepare_revision", prepare_revision_node)

    builder.add_edge(START, "coder")
    builder.add_conditional_edges("coder", route_from_coder)
    builder.add_edge("coder_tools", "coder")
    builder.add_conditional_edges("reviewer", route_from_reviewer)
    builder.add_edge("reviewer_tools", "reviewer")
    builder.add_edge("prepare_revision", "coder")

    return builder.compile(checkpointer=checkpointer)


def make_initial_state(prompt: str) -> WorkflowState:
    """Helper to build the initial state from a plain-text prompt."""
    return WorkflowState(
        messages=[HumanMessage(content=prompt)],
        iteration=0,
        verdict="",
    )
