"""
Validate and normalize workflow dicts into WorkflowConfig.

Raises ValueError with actionable messages on invalid topology.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
from pydantic import ValidationError

from autonode.core.workflow.models import (
    END_SENTINEL,
    RoutingReviewerFinishOrLoop,
    RoutingToolCallsOrNext,
    WorkflowConfig,
)


def parse_workflow_config(raw: dict[str, Any]) -> WorkflowConfig:
    """Parse a decoded YAML/JSON dict into WorkflowConfig."""

    try:
        config = WorkflowConfig(**raw)
        _validate_topology(config)
        return config
    except ValidationError as e:
        raise ValueError(f"[parse_workflow_config] Workflow config is invalid: {e}") from e


def _validate_topology(config: WorkflowConfig) -> None:
    """Validate the topology of the workflow."""

    G = nx.DiGraph()

    node_ids = {n.id for n in config.nodes}
    G.add_nodes_from(node_ids)
    G.add_node(END_SENTINEL)

    # Add fixed edges
    for edge in config.edges:
        G.add_edge(edge.from_node, edge.to)

    # Add conditional edges (routing) — include direct branches the runtime router can take.
    for node_id, rule in config.routing.items():
        if isinstance(rule, RoutingToolCallsOrNext):
            G.add_edge(node_id, rule.tools_node)
            G.add_edge(node_id, rule.next)
        if isinstance(rule, RoutingReviewerFinishOrLoop):
            G.add_edge(node_id, rule.tools_node)
            G.add_edge(node_id, rule.revision_node)
            G.add_edge(node_id, END_SENTINEL)

    # Check entry node exists
    if config.entry not in G:
        raise ValueError(f"[parse_workflow_config] Entry node '{config.entry}' not found in nodes")

    # Check if every node reachability
    for node in node_ids:
        if not nx.has_path(G, config.entry, node):
            raise ValueError(
                f"[parse_workflow_config] Entry node '{config.entry}' cannot reach node '{node}'"
            )
        if not nx.has_path(G, node, END_SENTINEL):
            raise ValueError(f"[parse_workflow_config] Node '{node}' cannot reach the end sentinel")

    # Check no isolated nodes
    isolates = [n for n in nx.isolates(G) if n != END_SENTINEL]
    if isolates:
        raise ValueError(f"[parse_workflow_config] Nodes {isolates} are isolated")
