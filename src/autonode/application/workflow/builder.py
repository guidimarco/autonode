"""
Build a compiled LangGraph StateGraph from WorkflowConfig.

Application layer: depends on core ports + workflow DTOs only (no infrastructure imports).
"""

from __future__ import annotations

import logging
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from autonode.application.workflow.state import GraphWorkflowState, default_review_verdict
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.models import (
    END_SENTINEL,
    AgentWorkflowNodeModel,
    RoutingReviewerFinishOrLoopModel,
    RoutingToolCallsOrNextModel,
    StateUpdateWorkflowNodeModel,
    ToolWorkflowNodeModel,
    VcsSyncWorkflowNodeModel,
    WorkflowModel,
    WorkflowNodeModel,
)
from autonode.core.workflow.ports import VCSProviderPort

logger = logging.getLogger(__name__)


def _edge_target(name: str) -> Any:
    return END if name == END_SENTINEL else name


def _resolve_tool_names_for_tool_node(
    node: ToolWorkflowNodeModel, factory: AgentFactoryPort
) -> list[str]:
    explicit = list(node.tool_names or [])
    aid = node.tools_agent_id
    if aid:
        from_agent = factory.tool_names_for_agent(aid)
        if explicit:
            return list(dict.fromkeys([*from_agent, *explicit]))
        return list(from_agent)
    return explicit


def _fallback_structured_review(reason: str) -> ReviewVerdictModel:
    return ReviewVerdictModel(
        is_approved=False,
        feedback=reason,
        missing_requirements=[],
    )


def build_graph(
    workflow: WorkflowModel,
    factory: AgentFactoryPort,
    registry: ToolRegistryPort,
    checkpointer: BaseCheckpointSaver[Any],
    *,
    vcs_provider: VCSProviderPort,
) -> Any:
    """
    Assemble and compile a StateGraph from workflow configuration.

    Checkpointer: pass a configured checkpointer from the application layer.
    """
    vcs: VCSProviderPort = vcs_provider

    nodes = workflow.nodes
    by_id: dict[str, WorkflowNodeModel] = {n.id: n for n in nodes}
    max_iterations = workflow.max_iterations

    builder = StateGraph(GraphWorkflowState)

    # ── Register nodes ───────────────────────────────────────────────────────

    for n in nodes:
        nid = n.id
        if isinstance(n, AgentWorkflowNodeModel):
            create_kw: dict[str, Any] = {}
            if n.structured_review:
                create_kw["structured_output_model"] = ReviewVerdictModel
            runnable = factory.create_agent(n.agent_id, **create_kw)
            builder.add_node(
                nid,
                _make_agent_node_fn(nid, n.agent_id, n.structured_review, runnable),
            )
        elif isinstance(n, ToolWorkflowNodeModel):
            tool_names = _resolve_tool_names_for_tool_node(n, factory)
            builder.add_node(nid, _make_dynamic_tool_node_fn(nid, tool_names, registry))
        elif isinstance(n, StateUpdateWorkflowNodeModel):
            builder.add_node(
                nid,
                _make_state_update_fn(
                    nid,
                    n.increment_iteration,
                    n.clear_verdict,
                ),
            )
        elif isinstance(n, VcsSyncWorkflowNodeModel):
            builder.add_node(nid, _make_vcs_sync_fn(nid, n, vcs))

    # ── Fixed edges ──────────────────────────────────────────────────────────

    builder.add_edge(START, workflow.entry)
    for e in workflow.edges or []:
        builder.add_edge(e.from_node, _edge_target(e.to))

    # ── Conditional routing ─────────────────────────────────────────────────

    for src, rule in (workflow.routing or {}).items():
        if src not in by_id:
            raise ValueError(f"workflow: routing source {src!r} not in nodes")
        if isinstance(rule, RoutingToolCallsOrNextModel):
            builder.add_conditional_edges(src, _make_tool_calls_or_next_router(src, rule))
        elif isinstance(rule, RoutingReviewerFinishOrLoopModel):
            builder.add_conditional_edges(
                src,
                _make_reviewer_router(src, rule, max_iterations),
            )
        else:
            raise ValueError(f"Unknown routing rule for {src!r}: {type(rule).__name__}")

    return builder.compile(checkpointer=checkpointer)


def _make_agent_node_fn(
    node_id: str,
    agent_id: str,
    structured_review: bool,
    agent_runnable: Any,
) -> Any:
    def agent_node(state: GraphWorkflowState) -> dict[str, Any]:
        logger.info(
            "[%s] agent=%s iteration=%s messages=%d",
            node_id,
            agent_id,
            state["iteration"],
            len(state["messages"]),
        )
        response = agent_runnable.invoke(state["messages"])
        if structured_review:
            if (
                isinstance(response, dict)
                and isinstance(response.get("message"), BaseMessage)
                and isinstance(response.get("review_verdict"), ReviewVerdictModel)
            ):
                raw_msg = cast(BaseMessage, response["message"])
                verdict = cast(ReviewVerdictModel, response["review_verdict"])
                out: dict[str, Any] = {
                    "messages": [raw_msg],
                    "review_verdict": verdict,
                    "current_node": node_id,
                }
            else:
                fallback_msg: BaseMessage
                if isinstance(response, BaseMessage):
                    fallback_msg = response
                else:
                    fallback_msg = AIMessage(content=str(response))
                out = {
                    "messages": [fallback_msg],
                    "review_verdict": _fallback_structured_review(
                        "Risposta strutturata reviewer mancante o non valida."
                    ),
                    "current_node": node_id,
                }
            logger.info(
                "[%s] structured review is_approved=%s",
                node_id,
                out["review_verdict"].is_approved,
            )
        else:
            msg_out: BaseMessage
            if isinstance(response, BaseMessage):
                msg_out = response
            else:
                msg_out = AIMessage(content=str(response))
            out = {"messages": [msg_out], "current_node": node_id}
        return out

    return agent_node


def _make_state_update_fn(node_id: str, increment_iteration: bool, clear_verdict: bool) -> Any:
    def state_update_node(state: GraphWorkflowState) -> dict[str, Any]:
        out: dict[str, Any] = {"current_node": node_id}
        if increment_iteration:
            new_iter = state["iteration"] + 1
            logger.info("[%s] iteration %s → %s", node_id, state["iteration"], new_iter)
            out["iteration"] = new_iter
        if clear_verdict:
            out["review_verdict"] = default_review_verdict()
        return out

    return state_update_node


def _make_dynamic_tool_node_fn(
    node_id: str, tool_names: list[str], registry: ToolRegistryPort
) -> Any:
    def tool_node(state: GraphWorkflowState) -> dict[str, Any]:
        execution_env = state.get("execution_env")
        if execution_env is None:
            raise RuntimeError(
                "Workflow state is missing execution_env; isolated sandbox is mandatory "
                "and host execution is disabled."
            )
        dynamic_registry: ToolRegistryPort = registry
        binder = getattr(registry, "bind_execution_environment", None)
        if callable(binder):
            dynamic_registry = cast(ToolRegistryPort, binder(execution_env))
        tools = dynamic_registry.get_tool_list_strict(tool_names)
        out = cast(dict[str, Any], ToolNode(tools).invoke(state))
        out["current_node"] = node_id
        return out

    return tool_node


def _make_vcs_sync_fn(
    node_id: str,
    node: VcsSyncWorkflowNodeModel,
    vcs: VCSProviderPort,
) -> Any:
    def sync_node(state: GraphWorkflowState) -> dict[str, Any]:
        raw_sid = state.get("session_id", "")
        sid = raw_sid if isinstance(raw_sid, str) else str(raw_sid)
        msg = node.commit_message.replace("{session_id}", sid)
        worktree = str(state.get("worktree_path", "") or "")
        commit_hash = vcs.commit_changes(worktree, msg)
        return {"last_commit_hash": commit_hash, "current_node": node_id}

    return sync_node


def _make_tool_calls_or_next_router(source_id: str, rule: RoutingToolCallsOrNextModel) -> Any:
    def route(state: GraphWorkflowState) -> Any:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            decision: Any = rule.tools_node
        else:
            decision = rule.next
        return _record_route(source_id, decision)

    return route


def _make_reviewer_router(
    source_id: str,
    rule: RoutingReviewerFinishOrLoopModel,
    max_iterations: int,
) -> Any:
    def route(state: GraphWorkflowState) -> Any:
        last: BaseMessage = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            decision: Any = rule.tools_node
        elif state["review_verdict"].is_approved or state["iteration"] >= max_iterations:
            logger.info(
                "[%s] done | is_approved=%s | iteration=%s",
                source_id,
                state["review_verdict"].is_approved,
                state["iteration"],
            )
            decision = END
        else:
            decision = rule.revision_node
        return _record_route(source_id, decision)

    return route


def _record_route(source_id: str, decision: Any) -> Any:
    label = END if decision is END else decision
    logger.debug("[%s] router -> %s", source_id, label)
    return decision
