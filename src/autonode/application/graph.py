"""
LangGraph entry: compile a workflow from WorkflowConfig (always supplied by caller).

Checkpointing: pass a checkpointer to build_graph; defaults to MemorySaver.
"""

from __future__ import annotations

from typing import Any

from autonode.application.graph_factory import compile_workflow
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.models import WorkflowConfig


def build_graph(
    workflow: WorkflowConfig,
    factory: AgentFactoryPort,
    registry: ToolRegistryPort,
    checkpointer: Any = None,
) -> Any:
    """
    Compile workflow from config.

    Invoke with:
        graph.invoke(
            make_initial_graph_state(prompt),
            config={"configurable": {"thread_id": "<task-id>"}},
        )
    """
    return compile_workflow(workflow, factory, registry, checkpointer)
