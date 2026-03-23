"""
Workflow configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; validated when building the graph.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

END_SENTINEL = "__end__"

# ── Post-workflow actions ──────────────────────────────────────────────────────

# Post-workflow actions are executed after the workflow is complete.
# This is defined what's happening after the workflow is complete.


@dataclass(frozen=True, slots=True)
class PostProcessStepModel:
    """Declarative post-workflow action (handled by post_processing runner, step 4)."""

    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerdictFromContentModel:
    """After agent reply, set `verdict` state from message content (case-insensitive)."""

    approved_marker: str
    approved_verdict: str
    revision_verdict: str


# ── Workflow nodes ─────────────────────────────────────────────────────────────

# Nodes are the building blocks of the workflow: agents, tools, and state updates.
# This is defined what's happening at each step of the workflow.


@dataclass(frozen=True, slots=True)
class AgentWorkflowNodeModel:
    id: str
    kind: Literal["agent"]
    agent_id: str
    verdict: VerdictFromContentModel | None = None


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
class VcsProvisionWorkflowNodeModel:
    """Prepare shadow worktree before coding agents run."""

    id: str
    kind: Literal["vcs_provision"]


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
    | VcsProvisionWorkflowNodeModel
    | VcsSyncWorkflowNodeModel
)


# ── Workflow edges ──────────────────────────────────────────────────────────────

# Edges are the connections between nodes.
# This is defined where the workflow should go next.


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

# The workflow model is the complete definition of the workflow.
# This is defined the entire workflow, including the nodes, edges, and routing.


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
