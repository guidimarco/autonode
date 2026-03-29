"""GraphWorkflowState telemetry fields (token budget / usage placeholders)."""

from __future__ import annotations

from pathlib import Path

from autonode.application.workflow.state import make_initial_graph_state
from autonode.core.constants import DEFAULT_TOKEN_BUDGET
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel


def test_make_initial_graph_state_sets_token_fields() -> None:
    repo = Path("/tmp/autonode-state-test-repo")
    workspace = WorkspaceBindingModel(
        session_id="550e8400-e29b-41d4-a716-446655440099",
        repo_host_path=str(repo),
        branch_name="autonode/session-test",
    )
    execution_env = ExecutionEnvironmentModel(
        session_id=workspace.session_id,
        sandbox_id=workspace.session_id,
        repo_host_path=str(repo),
    )
    s = make_initial_graph_state(
        "hello",
        execution_env=execution_env,
        workspace=workspace,
        total_tokens=0,
        token_budget=500_000,
    )
    assert s["total_tokens"] == 0
    assert s["token_budget"] == 500_000


def test_default_token_budget_matches_constant() -> None:
    repo = Path("/tmp/autonode-state-test-repo-2")
    workspace = WorkspaceBindingModel(
        session_id="550e8400-e29b-41d4-a716-446655440098",
        repo_host_path=str(repo),
        branch_name="autonode/session-test",
    )
    execution_env = ExecutionEnvironmentModel(
        session_id=workspace.session_id,
        sandbox_id=workspace.session_id,
        repo_host_path=str(repo),
    )
    s = make_initial_graph_state("x" * 10, execution_env=execution_env, workspace=workspace)
    assert s["total_tokens"] == 0
    assert s["token_budget"] == DEFAULT_TOKEN_BUDGET
