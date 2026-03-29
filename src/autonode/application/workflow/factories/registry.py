"""
Graph factory registry: named Python callables build compiled LangGraph graphs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.models import WorkflowModel
from autonode.core.workflow.ports import VCSProviderPort


@dataclass(frozen=True, slots=True)
class FactoryContext:
    """Inputs passed to a registered graph factory."""

    workflow: WorkflowModel
    agent_factory: AgentFactoryPort
    tool_registry: ToolRegistryPort
    vcs_provider: VCSProviderPort
    repo_root: Path | None = None
    checkpointer: Any = None


# Compiled LangGraph graph or compatible runnable; kept loose for factory return types.
GraphFactoryFn = Callable[[FactoryContext], Any]


FACTORY_REGISTRY: dict[str, GraphFactoryFn] = {}


def register_factory(name: str) -> Callable[[GraphFactoryFn], GraphFactoryFn]:
    """Decorator: register a graph factory under a stable string id (YAML `factory` field)."""

    def decorator(fn: GraphFactoryFn) -> GraphFactoryFn:
        if name in FACTORY_REGISTRY:
            raise ValueError(f"Duplicate factory registration: {name!r}")
        FACTORY_REGISTRY[name] = fn
        return fn

    return decorator


def get_registered_factory(name: str) -> GraphFactoryFn:
    """Return the factory for `name` or raise KeyError with a clear message."""
    try:
        return FACTORY_REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"No graph factory registered under name {name!r}") from e
