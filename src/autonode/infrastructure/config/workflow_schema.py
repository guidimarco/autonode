"""
Pydantic schemas for external configuration inputs.

Validation happens at the infrastructure boundary, then data is mapped to pure
core dataclasses via `to_core()`.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from autonode.core.workflow.models import (
    AgentWorkflowNodeModel,
    FixedEdgeModel,
    PostProcessStepModel,
    RoutingReviewerFinishOrLoopModel,
    RoutingToolCallsOrNextModel,
    StateUpdateWorkflowNodeModel,
    ToolWorkflowNodeModel,
    VcsSyncWorkflowNodeModel,
    WorkflowModel,
)


class PostProcessStepYamlSchema(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)

    def to_core(self) -> PostProcessStepModel:
        return PostProcessStepModel(action=self.action, params=dict(self.params))


class AgentWorkflowNodeYamlSchema(BaseModel):
    id: str
    kind: Literal["agent"]
    agent_id: str
    structured_review: bool = False

    model_config = ConfigDict(frozen=True)

    def to_core(self) -> AgentWorkflowNodeModel:
        return AgentWorkflowNodeModel(
            id=self.id,
            kind="agent",
            agent_id=self.agent_id,
            structured_review=self.structured_review,
        )


class ToolWorkflowNodeYamlSchema(BaseModel):
    id: str
    kind: Literal["tool_node"]
    tools_agent_id: str | None = None
    tool_names: list[str] | None = None

    model_config = ConfigDict(frozen=True)

    def to_core(self) -> ToolWorkflowNodeModel:
        return ToolWorkflowNodeModel(
            id=self.id,
            kind="tool_node",
            tools_agent_id=self.tools_agent_id,
            tool_names=list(self.tool_names) if self.tool_names is not None else None,
        )


class StateUpdateWorkflowNodeYamlSchema(BaseModel):
    id: str
    kind: Literal["state_update"]
    increment_iteration: bool = False
    clear_verdict: bool = False

    model_config = ConfigDict(frozen=True)

    def to_core(self) -> StateUpdateWorkflowNodeModel:
        return StateUpdateWorkflowNodeModel(
            id=self.id,
            kind="state_update",
            increment_iteration=self.increment_iteration,
            clear_verdict=self.clear_verdict,
        )


class VcsSyncWorkflowNodeYamlSchema(BaseModel):
    id: str
    kind: Literal["vcs_sync"]
    commit_message: str = "autonode: sync session {session_id}"

    model_config = ConfigDict(frozen=True)

    def to_core(self) -> VcsSyncWorkflowNodeModel:
        return VcsSyncWorkflowNodeModel(
            id=self.id,
            kind="vcs_sync",
            commit_message=self.commit_message,
        )


WorkflowNodeYamlSchema = Annotated[
    AgentWorkflowNodeYamlSchema
    | ToolWorkflowNodeYamlSchema
    | StateUpdateWorkflowNodeYamlSchema
    | VcsSyncWorkflowNodeYamlSchema,
    Field(discriminator="kind"),
]


class FixedEdgeYamlSchema(BaseModel):
    from_node: str
    to: str

    def to_core(self) -> FixedEdgeModel:
        return FixedEdgeModel(from_node=self.from_node, to=self.to)


class RoutingToolCallsOrNextYamlSchema(BaseModel):
    kind: Literal["tool_calls_or_next"]
    tools_node: str
    next: str

    def to_core(self) -> RoutingToolCallsOrNextModel:
        return RoutingToolCallsOrNextModel(
            kind="tool_calls_or_next",
            tools_node=self.tools_node,
            next=self.next,
        )


class RoutingReviewerFinishOrLoopYamlSchema(BaseModel):
    kind: Literal["reviewer_finish_or_tools_or_revision"]
    tools_node: str
    revision_node: str

    def to_core(self) -> RoutingReviewerFinishOrLoopModel:
        return RoutingReviewerFinishOrLoopModel(
            kind="reviewer_finish_or_tools_or_revision",
            tools_node=self.tools_node,
            revision_node=self.revision_node,
        )


RoutingRuleYamlSchema = Annotated[
    RoutingToolCallsOrNextYamlSchema | RoutingReviewerFinishOrLoopYamlSchema,
    Field(discriminator="kind"),
]


class WorkflowYamlSchema(BaseModel):
    version: Literal[1] = 1
    entry: str
    max_iterations: int = 3
    nodes: list[WorkflowNodeYamlSchema] = Field(default_factory=list)
    edges: list[FixedEdgeYamlSchema] = Field(default_factory=list)
    routing: dict[str, RoutingRuleYamlSchema] = Field(default_factory=dict)
    post_processing: list[PostProcessStepYamlSchema] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True, extra="ignore")

    def to_core(self) -> WorkflowModel:
        return WorkflowModel(
            version=self.version,
            entry=self.entry,
            max_iterations=self.max_iterations,
            nodes=[node.to_core() for node in self.nodes],
            edges=[edge.to_core() for edge in self.edges],
            routing={node_id: rule.to_core() for node_id, rule in self.routing.items()},
            post_processing=[step.to_core() for step in self.post_processing],
        )
