"""Reviewer routing with structured ReviewVerdictModel (no live LLM)."""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from autonode.application.workflow.factories import FactoryContext, get_registered_factory
from autonode.application.workflow.state import make_initial_graph_state
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel
from autonode.core.workflow import WorkflowModel
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory
from tests.stubs.session_logger import make_test_session_logger
from tests.stubs.vcs_provider import StubVcsProviderForCompileTests

_ROUTING_SID = "550e8400-e29b-41d4-a716-446655440004"


def _registry(tmp_path: Path) -> ToolRegistry:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = ExecutionEnvironmentModel(
        session_id=_ROUTING_SID,
        sandbox_id=_ROUTING_SID,
        repo_host_path=str(repo),
    )
    return ToolRegistry(execution_env=env, session_logger=make_test_session_logger())


def test_graph_invoke_reviewer_structured_approval_ends(
    workflow_config: WorkflowModel, tmp_path: Path
) -> None:
    """alpha → beta (structured approved) → router ends on is_approved."""
    factory = StubAgentFactory(
        structured_review_verdict=ReviewVerdictModel(
            is_approved=True,
            feedback="LGTM",
            missing_requirements=[],
        )
    )
    registry = _registry(tmp_path)
    factory_fn = get_registered_factory(workflow_config.factory)
    graph = factory_fn(
        FactoryContext(
            workflow=workflow_config,
            agent_factory=factory,
            tool_registry=registry,
            vcs_provider=StubVcsProviderForCompileTests(),
            checkpointer=InMemorySaver(),
        )
    )
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    workspace = WorkspaceBindingModel(
        session_id=_ROUTING_SID,
        repo_host_path=str(repo),
        branch_name="autonode/session-routing-test",
    )
    execution_env = ExecutionEnvironmentModel(
        session_id=_ROUTING_SID,
        sandbox_id=_ROUTING_SID,
        repo_host_path=str(repo),
    )
    initial = make_initial_graph_state(
        "task",
        execution_env=execution_env,
        workspace=workspace,
    )
    final = graph.invoke(
        initial,
        config={"configurable": {"thread_id": _ROUTING_SID}},
    )
    assert final["review_verdict"].is_approved is True
    assert final["review_verdict"].feedback == "LGTM"
