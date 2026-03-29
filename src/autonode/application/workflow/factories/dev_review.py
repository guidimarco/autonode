"""
Factory-driven developer/reviewer workflow with tool loops.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from autonode.application.agents.nodes import inject_agent_node, inject_tool_node, to_message
from autonode.application.workflow.factories.registry import FactoryContext, register_factory
from autonode.application.workflow.state import GraphWorkflowState, default_review_verdict
from autonode.core.agents.models import ReviewVerdictModel


@register_factory("dev_review_loop")
def build_dev_review_loop(ctx: FactoryContext) -> Any:
    """Builds developer -> reviewer loop with Command-based iteration updates."""
    params = dict(ctx.workflow.params)
    developer_id = str(params.get("developer_agent_id", "alpha_agent"))
    reviewer_id = str(params.get("reviewer_agent_id", "beta_agent"))
    max_iterations = ctx.workflow.max_iterations
    reviewer_structured = bool(params.get("reviewer_structured", True))
    developer_extra_tools = list(params.get("developer_tool_names", []))
    reviewer_extra_tools = list(params.get("reviewer_tool_names", []))

    reviewer = ctx.agent_factory.create_agent(
        reviewer_id,
        structured_output_model=ReviewVerdictModel if reviewer_structured else None,
    )

    graph = StateGraph(GraphWorkflowState)

    inject_agent_node(graph, "developer", ctx, developer_id)
    inject_tool_node(graph, "developer_tools", ctx, developer_id, developer_extra_tools)

    def reviewer_node(state: GraphWorkflowState) -> Command[str]:
        response = reviewer.invoke(state["messages"])
        verdict = default_review_verdict()
        message = to_message(response)
        if isinstance(response, dict):
            message = to_message(response.get("message"))
            raw_verdict = response.get("review_verdict")
            if isinstance(raw_verdict, ReviewVerdictModel):
                verdict = raw_verdict

        update: dict[str, Any] = {
            "messages": [message],
            "review_verdict": verdict,
            "current_node": "reviewer",
        }
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            return Command(goto="reviewer_tools", update=update)
        if verdict.is_approved or state["iteration"] >= max_iterations:
            return Command(goto=END, update=update)
        return Command(
            goto="developer",
            update={
                **update,
                "iteration": state["iteration"] + 1,
                "review_verdict": default_review_verdict(),
            },
        )

    graph.add_node("reviewer", reviewer_node)
    inject_tool_node(graph, "reviewer_tools", ctx, reviewer_id, reviewer_extra_tools)

    def developer_router(state: GraphWorkflowState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "developer_tools"
        return "reviewer"

    graph.add_edge(START, "developer")
    graph.add_edge("developer_tools", "developer")
    graph.add_edge("reviewer_tools", "reviewer")
    graph.add_conditional_edges("developer", developer_router)

    return graph.compile(checkpointer=ctx.checkpointer)
