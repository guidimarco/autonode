"""
LangGraph entry: compile a workflow from WorkflowConfig (always supplied by caller).

Checkpointing: pass a checkpointer to build_graph; defaults to MemorySaver.
"""

from __future__ import annotations

from typing import Any

from autonode.application.graph_factory import compile_workflow
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.models import WorkflowModel
from autonode.core.workflow.ports import VCSProviderPort


def build_graph(
    workflow: WorkflowModel,
    factory: AgentFactoryPort,
    registry: ToolRegistryPort,
    checkpointer: Any = None,
    *,
    vcs_provider: VCSProviderPort,
) -> Any:
    """
    Compile workflow from config.

    Invoke with initial state from ``make_initial_graph_state`` (execution_env + workspace
    from CLI bootstrap) and ``config={"configurable": {"thread_id": "<task-id>"}}``.
    """
    return compile_workflow(
        workflow,
        factory,
        registry,
        checkpointer,
        vcs_provider=vcs_provider,
    )
