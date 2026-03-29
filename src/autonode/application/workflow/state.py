"""
LangGraph shared state for configuration-driven workflows.

Designed for checkpointers: keep serializable-friendly values in context/artifacts;
messages use LangGraph's add_messages reducer.
"""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.constants import DEFAULT_TOKEN_BUDGET
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel


def _merge_shallow(left: dict[str, Any], right: dict[str, Any] | None) -> dict[str, Any]:
    if right is None:
        return left
    return {**left, **right}


def default_review_verdict() -> ReviewVerdictModel:
    """Initial / cleared reviewer state (not approved, no feedback)."""
    return ReviewVerdictModel(
        is_approved=False,
        feedback="",
        missing_requirements=[],
    )


class GraphWorkflowState(TypedDict):
    """Extensible workflow state (short-term / thread memory via checkpointer)."""

    messages: Annotated[list[BaseMessage], add_messages]
    iteration: int
    review_verdict: ReviewVerdictModel
    context: Annotated[dict[str, Any], _merge_shallow]
    artifacts: Annotated[dict[str, Any], _merge_shallow]
    execution_env: ExecutionEnvironmentModel
    session_id: str
    worktree_path: str
    branch_name: str
    status: NotRequired[str]
    current_node: NotRequired[str]
    last_router_decision: NotRequired[str]
    total_tokens: int
    token_budget: int


def make_initial_graph_state(
    prompt: str,
    *,
    execution_env: ExecutionEnvironmentModel,
    workspace: WorkspaceBindingModel,
    context: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    total_tokens: int = 0,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> GraphWorkflowState:
    """Build initial state for invoke/stream with thread_id in config."""
    if workspace.session_id != execution_env.session_id:
        raise ValueError("workspace.session_id must match execution_env.session_id")
    if workspace.worktree_host_path != execution_env.worktree_host_path:
        raise ValueError("workspace.worktree_host_path must match execution_env.worktree_host_path")
    ctx = dict(context or {})
    ctx.setdefault("vcs_repo_path", workspace.repo_host_path)
    ctx.setdefault("worktree_path", workspace.worktree_host_path)
    return GraphWorkflowState(
        messages=[HumanMessage(content=prompt)],
        iteration=0,
        review_verdict=default_review_verdict(),
        context=ctx,
        artifacts=artifacts or {},
        execution_env=execution_env,
        session_id=workspace.session_id,
        worktree_path=workspace.worktree_host_path,
        branch_name=workspace.branch_name,
        total_tokens=total_tokens,
        token_budget=token_budget,
    )
