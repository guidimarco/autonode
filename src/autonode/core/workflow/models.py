"""
Workflow configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; validated when building the graph.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

END_SENTINEL = "__end__"

# ── Post-workflow actions ──────────────────────────────────────────────────────

# Post-workflow actions are executed after the workflow is complete.
# This is defined what's happening after the workflow is complete.


class PostProcessStepConfig(BaseModel):
    """Declarative post-workflow action (handled by post_processing runner, step 4)."""

    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class VerdictFromContentConfig(BaseModel):
    """After agent reply, set `verdict` state from message content (case-insensitive)."""

    approved_marker: str = Field(..., description="The marker to use to approve the content.")
    approved_verdict: str = Field(..., description="The verdict to use to approve the content.")
    revision_verdict: str = Field(..., description="The verdict to use to revision the content.")


# ── Workflow nodes ─────────────────────────────────────────────────────────────

# Nodes are the building blocks of the workflow: agents, tools, and state updates.
# This is defined what's happening at each step of the workflow.


class AgentWorkflowNode(BaseModel):
    id: str
    kind: Literal["agent"] = Field(..., description="The kind of the node.")
    agent_id: str = Field(..., description="The agent ID to use for the node.")
    verdict: VerdictFromContentConfig | None = Field(
        None, description="The verdict to use for the node."
    )


class ToolWorkflowNode(BaseModel):
    id: str
    kind: Literal["tool_node"] = Field(..., description="The kind of the node.")
    tools_agent_id: str | None = Field(None, description="The agent ID to use for the tools.")
    tool_names: list[str] | None = Field(None, description="The tools to use for the node.")


class StateUpdateWorkflowNode(BaseModel):
    id: str
    kind: Literal["state_update"] = Field(..., description="The kind of the node.")
    increment_iteration: bool = Field(False, description="Whether to increment the iteration.")
    clear_verdict: bool = Field(False, description="Whether to clear the verdict.")


class VcsProvisionWorkflowNode(BaseModel):
    """Prepare shadow worktree before coding agents run."""

    id: str
    kind: Literal["vcs_provision"] = Field(..., description="The kind of the node.")


class VcsSyncWorkflowNode(BaseModel):
    """Commit (and optionally push) session worktree after a successful edit round."""

    id: str
    kind: Literal["vcs_sync"] = Field(..., description="The kind of the node.")
    commit_message: str = Field(
        default="autonode: sync session {session_id}",
        description="Commit message template; {session_id} is substituted when present.",
    )


WorkflowNodeConfig = Annotated[
    AgentWorkflowNode
    | ToolWorkflowNode
    | StateUpdateWorkflowNode
    | VcsProvisionWorkflowNode
    | VcsSyncWorkflowNode,
    Field(..., discriminator="kind", description="The node configuration."),
]


# ── Workflow edges ──────────────────────────────────────────────────────────────

# Edges are the connections between nodes.
# This is defined where the workflow should go next.


class FixedEdgeConfig(BaseModel):
    from_node: str = Field(..., description="The node ID to start from.")
    to: str = Field(..., description="The node ID to go to.")


class RoutingToolCallsOrNext(BaseModel):
    kind: Literal["tool_calls_or_next"] = Field(..., description="The kind of the routing.")
    tools_node: str = Field(..., description="The node ID to use for the tools.")
    next: str = Field(..., description="The node ID to go to next.")


class RoutingReviewerFinishOrLoop(BaseModel):
    kind: Literal["reviewer_finish_or_tools_or_revision"] = Field(
        ..., description="The kind of the routing."
    )
    tools_node: str = Field(..., description="The node ID to use for the tools.")
    revision_node: str = Field(..., description="The node ID to go to revision.")


RoutingRule = Annotated[
    RoutingToolCallsOrNext | RoutingReviewerFinishOrLoop,
    Field(..., discriminator="kind", description="The routing configuration."),
]


# ── Workflow configuration ──────────────────────────────────────────────────────

# The workflow configuration is the complete definition of the workflow.
# This is defined the entire workflow, including the nodes, edges, and routing.


class WorkflowConfig(BaseModel):
    """Full workflow definition: topology + routing; agent identities stay in agents.yaml."""

    version: Literal[1] = Field(1, description="The version of the workflow.")
    entry: str = Field(..., description="The entry node of the workflow.")
    max_iterations: int = Field(3, description="The maximum number of iterations of the workflow.")
    nodes: list[WorkflowNodeConfig] = Field(
        default_factory=list, description="The nodes of the workflow."
    )
    edges: list[FixedEdgeConfig] = Field(
        default_factory=list, description="The edges of the workflow."
    )
    routing: dict[str, RoutingRule] = Field(
        default_factory=dict, description="The routing of the workflow."
    )
    post_processing: list[PostProcessStepConfig] = Field(
        default_factory=list, description="The post-processing of the workflow."
    )

    model_config = ConfigDict(extra="ignore")
