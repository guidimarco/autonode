"""Workflow config parsing and graph compilation (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.application.graph_factory import compile_workflow
from autonode.core.workflow import WorkflowModel
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory


def test_load_testdata_workflow(workflow_config: WorkflowModel) -> None:
    assert workflow_config.entry == "alpha"
    assert len(workflow_config.nodes) == 5
    assert len(workflow_config.post_processing) >= 1


def _registry_root(tmp_path: Path) -> str:
    root = tmp_path / "sandbox"
    root.mkdir()
    return str(root)


def test_compile_workflow_from_testdata(
    workflow_config: WorkflowModel, stub_agent_factory: StubAgentFactory, tmp_path: Path
) -> None:
    registry = ToolRegistry(root_dir=_registry_root(tmp_path))
    graph = compile_workflow(workflow_config, stub_agent_factory, registry, checkpointer=None)
    assert graph is not None


def test_get_tool_list_strict_unknown_raises(tmp_path: Path) -> None:
    registry = ToolRegistry(root_dir=_registry_root(tmp_path))
    with pytest.raises(ValueError, match="Tool non registrati"):
        registry.get_tool_list_strict(["nonexistent_tool_xyz"])
