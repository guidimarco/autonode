"""Workflow config parsing and graph compilation (no live LLM)."""

from __future__ import annotations

import pytest

from autonode.application.graph_factory import compile_workflow
from autonode.core.workflow import WorkflowConfig, parse_workflow_config
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory


def test_load_testdata_workflow(workflow_config: WorkflowConfig) -> None:
    assert workflow_config.entry == "alpha"
    assert len(workflow_config.nodes) == 5
    assert len(workflow_config.post_processing) >= 1


def test_parse_rejects_bad_version() -> None:
    bad = {
        "version": 2,
        "entry": "a",
        "nodes": [{"id": "a", "kind": "agent", "agent_id": "x"}],
    }
    with pytest.raises(ValueError, match="version"):
        parse_workflow_config(bad)


def test_compile_workflow_from_testdata(
    workflow_config: WorkflowConfig, stub_agent_factory: StubAgentFactory
) -> None:
    registry = ToolRegistry(root_dir="./playground")
    graph = compile_workflow(workflow_config, stub_agent_factory, registry, checkpointer=None)
    assert graph is not None


def test_get_tool_list_strict_unknown_raises() -> None:
    registry = ToolRegistry(root_dir="./playground")
    with pytest.raises(ValueError, match="Tool non registrati"):
        registry.get_tool_list_strict(["nonexistent_tool_xyz"])
