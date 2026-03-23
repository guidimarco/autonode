"""Workflow config parsing and graph compilation (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autonode.application.graph_factory import compile_workflow
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.workflow import WorkflowModel
from autonode.core.workflow.models import VcsProvisionWorkflowNodeModel
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory
from tests.stubs.vcs_provider import StubVcsProviderForCompileTests


def _registry_for_compile(tmp_path: Path) -> ToolRegistry:
    root = tmp_path / "sandbox"
    root.mkdir()
    env = ExecutionEnvironmentModel(
        session_id="compile-test",
        sandbox_id="fixture-compile-only",
        worktree_host_path=str(root),
        container_workspace_path="/workspace",
    )
    return ToolRegistry(execution_env=env)


def _vcs_for_compile() -> StubVcsProviderForCompileTests:
    return StubVcsProviderForCompileTests()


def test_load_testdata_workflow(workflow_config: WorkflowModel) -> None:
    assert workflow_config.entry == "alpha"
    assert len(workflow_config.nodes) == 5
    assert len(workflow_config.post_processing) >= 1


def test_compile_workflow_from_testdata(
    workflow_config: WorkflowModel, stub_agent_factory: StubAgentFactory, tmp_path: Path
) -> None:
    registry = _registry_for_compile(tmp_path)
    graph = compile_workflow(
        workflow_config,
        stub_agent_factory,
        registry,
        checkpointer=None,
        vcs_provider=_vcs_for_compile(),
    )
    assert graph is not None


def test_compile_rejects_vcs_provision_node(
    stub_agent_factory: StubAgentFactory, tmp_path: Path
) -> None:
    wf = WorkflowModel(
        entry="p",
        nodes=[VcsProvisionWorkflowNodeModel(id="p", kind="vcs_provision")],
        edges=[],
    )
    registry = _registry_for_compile(tmp_path)
    with pytest.raises(ValueError, match="vcs_provision"):
        compile_workflow(
            wf,
            stub_agent_factory,
            registry,
            checkpointer=None,
            vcs_provider=_vcs_for_compile(),
        )


def test_get_tool_list_strict_unknown_raises(tmp_path: Path) -> None:
    registry = _registry_for_compile(tmp_path)
    with pytest.raises(ValueError, match="Tool non registrati"):
        registry.get_tool_list_strict(["nonexistent_tool_xyz"])
