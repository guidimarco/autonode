"""Reviewer routing with structured ReviewVerdictModel (no live LLM)."""

from __future__ import annotations

from pathlib import Path

from autonode.application.workflow.builder import build_graph
from autonode.application.workflow.state import make_initial_graph_state
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel
from autonode.core.workflow import WorkflowModel
from autonode.infrastructure.tools.registry import ToolRegistry
from tests.stubs.agent_factory import StubAgentFactory
from tests.stubs.vcs_provider import StubVcsProviderForCompileTests


def _registry(tmp_path: Path) -> ToolRegistry:
    root = tmp_path / "sandbox"
    root.mkdir()
    env = ExecutionEnvironmentModel(
        session_id="routing-test",
        sandbox_id="routing-test",
        worktree_host_path=str(root),
        container_workspace_path="/workspace",
    )
    return ToolRegistry(execution_env=env)


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
    graph = build_graph(
        workflow_config,
        factory,
        registry,
        checkpointer=None,
        vcs_provider=StubVcsProviderForCompileTests(),
    )
    sandbox_root = tmp_path / "sandbox"
    sandbox_root.mkdir(exist_ok=True)
    workspace = WorkspaceBindingModel(
        session_id="routing-test",
        repo_host_path=str(tmp_path),
        worktree_host_path=str(sandbox_root),
        branch_name="autonode/session-routing-test",
    )
    execution_env = ExecutionEnvironmentModel(
        session_id="routing-test",
        sandbox_id="routing-test",
        worktree_host_path=str(sandbox_root),
        container_workspace_path="/workspace",
    )
    initial = make_initial_graph_state(
        "task",
        execution_env=execution_env,
        workspace=workspace,
    )
    final = graph.invoke(
        initial,
        config={"configurable": {"thread_id": "routing-test"}},
    )
    assert final["review_verdict"].is_approved is True
    assert final["review_verdict"].feedback == "LGTM"
