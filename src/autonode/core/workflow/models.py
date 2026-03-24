"""
Workflow configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; validated when building the graph.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

END_SENTINEL = "__end__"

# ── Post-workflow actions ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PostProcessStepModel:
    """Declarative post-workflow action (handled by post_processing runner)."""

    action: str
    params: dict[str, Any] = field(default_factory=dict)


# ── Workflow nodes ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AgentWorkflowNodeModel:
    id: str
    kind: Literal["agent"]
    agent_id: str
    structured_review: bool = False


@dataclass(frozen=True, slots=True)
class ToolWorkflowNodeModel:
    id: str
    kind: Literal["tool_node"]
    tools_agent_id: str | None = None
    tool_names: list[str] | None = None


@dataclass(frozen=True, slots=True)
class StateUpdateWorkflowNodeModel:
    id: str
    kind: Literal["state_update"]
    increment_iteration: bool = False
    clear_verdict: bool = False


@dataclass(frozen=True, slots=True)
class VcsSyncWorkflowNodeModel:
    """Commit (and optionally push) session worktree after a successful edit round."""

    id: str
    kind: Literal["vcs_sync"]
    commit_message: str = "autonode: sync session {session_id}"


WorkflowNodeModel = (
    AgentWorkflowNodeModel
    | ToolWorkflowNodeModel
    | StateUpdateWorkflowNodeModel
    | VcsSyncWorkflowNodeModel
)


# ── Workflow edges ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FixedEdgeModel:
    from_node: str
    to: str


@dataclass(frozen=True, slots=True)
class RoutingToolCallsOrNextModel:
    kind: Literal["tool_calls_or_next"]
    tools_node: str
    next: str


@dataclass(frozen=True, slots=True)
class RoutingReviewerFinishOrLoopModel:
    kind: Literal["reviewer_finish_or_tools_or_revision"]
    tools_node: str
    revision_node: str


RoutingRule = RoutingToolCallsOrNextModel | RoutingReviewerFinishOrLoopModel


# ── Workflow model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WorkflowModel:
    """Full workflow definition: topology + routing; agent identities stay in agents.yaml."""

    version: Literal[1] = 1
    entry: str = ""
    max_iterations: int = 3
    nodes: list[WorkflowNodeModel] = field(default_factory=list)
    edges: list[FixedEdgeModel] = field(default_factory=list)
    routing: dict[str, RoutingRule] = field(default_factory=dict)
    post_processing: list[PostProcessStepModel] = field(default_factory=list)
