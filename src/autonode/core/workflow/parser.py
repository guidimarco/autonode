"""
Validate and normalize workflow dicts into WorkflowConfig.

Raises ValueError with actionable messages on invalid topology.
"""

from __future__ import annotations

import networkx as nx

from autonode.core.workflow.models import (
    END_SENTINEL,
    RoutingReviewerFinishOrLoopModel,
    RoutingToolCallsOrNextModel,
    WorkflowModel,
)


def parse_workflow(workflow: WorkflowModel) -> WorkflowModel:
    if workflow.version != 1:
        raise ValueError("[parse_workflow] Workflow model is invalid: version must be 1")
    _validate_topology(workflow)
    return workflow


def _validate_topology(workflow: WorkflowModel) -> None:
    """Validate the topology of the workflow."""

    G = nx.DiGraph()

    node_ids = {n.id for n in workflow.nodes}
    G.add_nodes_from(node_ids)
    G.add_node(END_SENTINEL)

    # Add fixed edges
    for edge in workflow.edges:
        G.add_edge(edge.from_node, edge.to)

    # Add conditional edges (routing) — include direct branches the runtime router can take.
    for node_id, rule in workflow.routing.items():
        if isinstance(rule, RoutingToolCallsOrNextModel):
            G.add_edge(node_id, rule.tools_node)
            G.add_edge(node_id, rule.next)
        if isinstance(rule, RoutingReviewerFinishOrLoopModel):
            G.add_edge(node_id, rule.tools_node)
            G.add_edge(node_id, rule.revision_node)
            G.add_edge(node_id, END_SENTINEL)

    # Check entry node exists
    if workflow.entry not in G:
        raise ValueError(
            f"[parse_workflow_config] Entry node '{workflow.entry}' not found in nodes"
        )

    # Check if every node reachability
    for node in node_ids:
        if not nx.has_path(G, workflow.entry, node):
            raise ValueError(
                f"[parse_workflow_config] Entry node '{workflow.entry}' cannot reach node '{node}'"
            )
        if not nx.has_path(G, node, END_SENTINEL):
            raise ValueError(f"[parse_workflow_config] Node '{node}' cannot reach the end sentinel")

    # Check no isolated nodes
    isolates = [n for n in nx.isolates(G) if n != END_SENTINEL]
    if isolates:
        raise ValueError(f"[parse_workflow_config] Nodes {isolates} are isolated")
