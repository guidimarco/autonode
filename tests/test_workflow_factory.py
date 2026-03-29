"""Workflow config parsing and graph compilation (no live LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from autonode.application.workflow.factories import FactoryContext, get_registered_factory
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.workflow import WorkflowModel
from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory
from tests.stubs.session_logger import make_test_session_logger
from tests.stubs.vcs_provider import StubVcsProviderForCompileTests

_COMPILE_SID = "550e8400-e29b-41d4-a716-446655440003"


def _registry_for_compile(tmp_path: Path) -> ToolRegistry:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = ExecutionEnvironmentModel(
        session_id=_COMPILE_SID,
        sandbox_id="fixture-compile-only",
        repo_host_path=str(repo),
    )
    return ToolRegistry(execution_env=env, session_logger=make_test_session_logger())


def _vcs_for_compile() -> StubVcsProviderForCompileTests:
    return StubVcsProviderForCompileTests()


def test_load_testdata_workflow(workflow_config: WorkflowModel) -> None:
    assert workflow_config.factory == "dev_review_loop"
    assert workflow_config.max_iterations == 10
    assert workflow_config.token_budget == 500_000
    assert isinstance(workflow_config.post_processing, list)
    assert workflow_config.params["reviewer_structured"] is True


def test_compile_workflow_from_testdata(
    workflow_config: WorkflowModel, stub_agent_factory: StubAgentFactory, tmp_path: Path
) -> None:
    registry = _registry_for_compile(tmp_path)
    factory_fn = get_registered_factory(workflow_config.factory)
    graph = factory_fn(
        FactoryContext(
            workflow=workflow_config,
            agent_factory=stub_agent_factory,
            tool_registry=registry,
            vcs_provider=_vcs_for_compile(),
            checkpointer=InMemorySaver(),
        )
    )
    assert graph is not None


def test_workflow_schema_rejects_legacy_topology_fields() -> None:
    raw = {"version": 2, "factory": "dev_review_loop", "nodes": [{"id": "p"}]}
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        WorkflowYamlSchema.model_validate(raw)


def test_get_registered_factory_unknown_name_raises() -> None:
    """YAML may name any factory string; resolution fails if not in FACTORY_REGISTRY."""
    with pytest.raises(KeyError, match="No graph factory registered"):
        get_registered_factory("unregistered_factory_xyz")


def test_get_tool_list_strict_unknown_raises(tmp_path: Path) -> None:
    registry = _registry_for_compile(tmp_path)
    with pytest.raises(ValueError, match="Tool non registrati"):
        registry.get_tool_list_strict(["nonexistent_tool_xyz"])
