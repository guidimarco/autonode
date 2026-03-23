"""
Build a compiled LangGraph StateGraph from WorkflowConfig.

Application layer: depends on core ports + workflow DTOs only (no infrastructure imports).
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from autonode.application.workflow_state import GraphWorkflowState
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.models import (
    END_SENTINEL,
    AgentWorkflowNodeModel,
    RoutingReviewerFinishOrLoopModel,
    RoutingToolCallsOrNextModel,
    StateUpdateWorkflowNodeModel,
    ToolWorkflowNodeModel,
    VcsProvisionWorkflowNodeModel,
    VcsSyncWorkflowNodeModel,
    VerdictFromContentModel,
    WorkflowModel,
    WorkflowNodeModel,
)
from autonode.core.workflow.ports import NoOpVcsProvider, VCSProviderPort

logger = logging.getLogger(__name__)


def _edge_target(name: str) -> Any:
    return END if name == END_SENTINEL else name


def _branch_label_for_session(session_id: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", session_id.strip()).strip("-") or "session"
    return f"autonode/session-{token[:80]}"


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


def compile_workflow(
    workflow: WorkflowModel,
    factory: AgentFactoryPort,
    registry: ToolRegistryPort,
    checkpointer: Any = None,
    *,
    vcs_provider: VCSProviderPort | None = None,
    vcs_repo_path: str | None = None,
) -> Any:
    """
    Assemble and compile a StateGraph from workflow configuration.

    Checkpointer: pass None for default MemorySaver; use SqliteSaver/Postgres for persistence.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    vcs: VCSProviderPort = vcs_provider if vcs_provider is not None else NoOpVcsProvider()
    repo_path = vcs_repo_path if vcs_repo_path is not None else "."

    nodes = workflow.nodes
    by_id: dict[str, WorkflowNodeModel] = {n.id: n for n in nodes}
    max_iterations = workflow.max_iterations

    builder = StateGraph(GraphWorkflowState)

    # ── Register nodes ───────────────────────────────────────────────────────

    for n in nodes:
        nid = n.id
        if isinstance(n, AgentWorkflowNodeModel):
            runnable = factory.create_agent(n.agent_id)
            verdict_cfg = n.verdict
            builder.add_node(
                nid,
                _make_agent_node_fn(nid, n.agent_id, verdict_cfg, runnable),
            )
        elif isinstance(n, ToolWorkflowNodeModel):
            tool_names = _resolve_tool_names_for_tool_node(n, factory)
            tools = registry.get_tool_list_strict(tool_names)
            builder.add_node(nid, ToolNode(tools))
        elif isinstance(n, StateUpdateWorkflowNodeModel):
            builder.add_node(
                nid,
                _make_state_update_fn(
                    nid,
                    n.increment_iteration,
                    n.clear_verdict,
                ),
            )
        elif isinstance(n, VcsProvisionWorkflowNodeModel):
            builder.add_node(nid, _make_vcs_provision_fn(nid, vcs, repo_path))
        elif isinstance(n, VcsSyncWorkflowNodeModel):
            builder.add_node(nid, _make_vcs_sync_fn(nid, n, vcs))
        else:
            raise ValueError(f"Unsupported node kind for id {nid!r}")

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
            builder.add_conditional_edges(src, _make_reviewer_router(src, rule, max_iterations))
        else:
            raise ValueError(f"Unknown routing rule for {src!r}: {type(rule).__name__}")

    return builder.compile(checkpointer=checkpointer)


def _make_agent_node_fn(
    node_id: str,
    agent_id: str,
    verdict_cfg: VerdictFromContentModel | None,
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
        out: dict[str, Any] = {"messages": [response], "current_node": node_id}
        if verdict_cfg:
            content = response.content if isinstance(response.content, str) else ""
            marker = verdict_cfg.approved_marker.upper()
            approved = marker in content.upper()
            if approved:
                out["verdict"] = verdict_cfg.approved_verdict
            else:
                out["verdict"] = verdict_cfg.revision_verdict
            logger.info("[%s] verdict=%s", node_id, out["verdict"])
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
            out["verdict"] = ""
        return out

    return state_update_node


def _make_vcs_provision_fn(node_id: str, vcs: VCSProviderPort, repo_path: str) -> Any:
    def provision_node(state: GraphWorkflowState) -> dict[str, Any]:
        raw_sid = state.get("session_id")
        sid = str(raw_sid) if raw_sid else str(uuid.uuid4())
        wt = vcs.setup_session_worktree(sid, repo_path)
        branch = getattr(vcs, "branch_name", None)
        if isinstance(branch, str) and branch:
            bn = branch
        else:
            bn = _branch_label_for_session(sid)
        out: dict[str, Any] = {
            "session_id": sid,
            "worktree_path": wt,
            "branch_name": bn,
            "current_node": node_id,
        }
        ctx = dict(state.get("context") or {})
        ctx["vcs_repo_path"] = repo_path
        ctx["worktree_path"] = wt
        out["context"] = ctx
        return out

    return provision_node


def _make_vcs_sync_fn(node_id: str, node: VcsSyncWorkflowNodeModel, vcs: VCSProviderPort) -> Any:
    def sync_node(state: GraphWorkflowState) -> dict[str, Any]:
        raw_sid = state.get("session_id", "")
        sid = raw_sid if isinstance(raw_sid, str) else str(raw_sid)
        msg = node.commit_message.replace("{session_id}", sid)
        commit_hash = vcs.commit_and_push(msg, push=True)
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
    source_id: str, rule: RoutingReviewerFinishOrLoopModel, max_iterations: int
) -> Any:
    def route(state: GraphWorkflowState) -> Any:
        last: BaseMessage = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            decision: Any = rule.tools_node
        elif state["verdict"] == "approved" or state["iteration"] >= max_iterations:
            logger.info(
                "[%s] done | verdict=%s | iteration=%s",
                source_id,
                state["verdict"],
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
