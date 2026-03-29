"""
Reusable LangGraph node injectors for agent invoke loops and dynamic ToolNode wiring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from autonode.application.workflow.state import GraphWorkflowState
from autonode.core.tools.ports import ToolRegistryPort

if TYPE_CHECKING:
    from autonode.application.workflow.factories.registry import FactoryContext


def to_message(response: Any) -> BaseMessage:
    """Normalize agent outputs to a single assistant message."""
    if isinstance(response, BaseMessage):
        return response
    return AIMessage(content=str(response))


def resolve_tool_names(
    ctx: FactoryContext, agent_id: str, extra: list[str] | None = None
) -> list[str]:
    """Merge tool ids from agent config with optional extras, preserving order, deduping."""
    from_agent = ctx.agent_factory.tool_names_for_agent(agent_id)
    extras = extra or []
    return list(dict.fromkeys([*from_agent, *extras]))


def inject_agent_node(
    graph: StateGraph[Any],
    node_id: str,
    ctx: FactoryContext,
    agent_id: str,
    output_model: Any = None,
) -> None:
    """Add a node that invokes an agent and appends one message plus ``current_node``."""
    agent = ctx.agent_factory.create_agent(
        agent_id,
        structured_output_model=output_model,
    )

    def node_fn(state: GraphWorkflowState) -> dict[str, Any]:
        response = agent.invoke(state["messages"])
        return {"messages": [to_message(response)], "current_node": node_id}

    graph.add_node(node_id, node_fn)


def inject_tool_node(
    graph: StateGraph[Any],
    node_id: str,
    ctx: FactoryContext,
    agent_id: str,
    extra_tools: list[str] | None = None,
) -> None:
    """Add a ToolNode with registry tools resolved for the agent id plus optional extras."""
    tool_names = resolve_tool_names(ctx, agent_id, extra_tools)
    registry = ctx.tool_registry

    def tool_fn(state: GraphWorkflowState) -> dict[str, Any]:
        execution_env = state.get("execution_env")
        if execution_env is None:
            raise RuntimeError("Workflow state is missing execution_env.")
        binder = getattr(registry, "bind_execution_environment", None)
        dynamic_registry = (
            cast(ToolRegistryPort, binder(execution_env)) if callable(binder) else registry
        )
        tools = dynamic_registry.get_tool_list_strict(tool_names)
        out = cast(dict[str, Any], ToolNode(tools).invoke(state))
        out["current_node"] = node_id
        return out

    graph.add_node(node_id, tool_fn)
