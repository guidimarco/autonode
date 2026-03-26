"""RunWorkflowUseCase: cleanup deterministico e risposta con branch di sessione."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from autonode.application.use_cases.run_workflow_uc import (
    RunWorkflowUseCase,
    RunWorkflowUseCaseRequest,
)
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel
from autonode.core.tools.ports import ToolRegistryPort


@pytest.fixture
def workspace_binding() -> WorkspaceBindingModel:
    return WorkspaceBindingModel(
        session_id="sid-1",
        repo_host_path="/repo",
        worktree_host_path="/repo/.autonode/worktrees/sid-1",
        branch_name="autonode/session-sid-1",
    )


@pytest.fixture
def execution_env(workspace_binding: WorkspaceBindingModel) -> ExecutionEnvironmentModel:
    return ExecutionEnvironmentModel(
        session_id=workspace_binding.session_id,
        sandbox_id="container-abc",
        worktree_host_path=workspace_binding.worktree_host_path,
        container_workspace_path="/workspace",
    )


def test_execute_releases_container_then_removes_worktree(
    workspace_binding: WorkspaceBindingModel,
    execution_env: ExecutionEnvironmentModel,
) -> None:
    events: list[str] = []

    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.return_value = execution_env
    sandbox.release_environment.side_effect = lambda env: events.append("release")
    vcs.remove_session_worktree.side_effect = lambda rp, sid: events.append("remove")

    def registry_factory(env: ExecutionEnvironmentModel) -> ToolRegistryPort:
        return cast(ToolRegistryPort, MagicMock())

    def agent_factory_provider(path: str, registry: ToolRegistryPort) -> AgentFactoryPort:
        return cast(AgentFactoryPort, MagicMock())

    graph = MagicMock()
    graph.invoke.return_value = {
        "messages": [AIMessage(content="ok")],
        "review_verdict": ReviewVerdictModel(
            is_approved=True,
            feedback="",
            missing_requirements=[],
        ),
        "iteration": 0,
        "last_commit_hash": "abc",
    }

    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch(
            "autonode.application.use_cases.run_workflow_uc.build_graph",
            return_value=graph,
        ):
            uc = RunWorkflowUseCase(
                vcs, sandbox, registry_factory, agent_factory_provider, checkpointer=MagicMock()
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id="sid-1",
            )
            out = uc.execute(req)

    assert out.branch_name == workspace_binding.branch_name
    assert events == ["release", "remove"]
    sandbox.release_environment.assert_called_once_with(execution_env)
    vcs.remove_session_worktree.assert_called_once_with("/repo", "sid-1")
    vcs.delete_session_branch.assert_not_called()


def test_execute_cleanup_after_graph_raises(
    workspace_binding: WorkspaceBindingModel,
    execution_env: ExecutionEnvironmentModel,
) -> None:
    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.return_value = execution_env

    graph = MagicMock()
    graph.invoke.side_effect = RuntimeError("graph failed")

    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch(
            "autonode.application.use_cases.run_workflow_uc.build_graph",
            return_value=graph,
        ):

            def registry_factory(env: ExecutionEnvironmentModel) -> ToolRegistryPort:
                return cast(ToolRegistryPort, MagicMock())

            def agent_factory_provider(path: str, registry: ToolRegistryPort) -> AgentFactoryPort:
                return cast(AgentFactoryPort, MagicMock())

            uc = RunWorkflowUseCase(
                vcs, sandbox, registry_factory, agent_factory_provider, checkpointer=MagicMock()
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id="sid-1",
            )
            with pytest.raises(RuntimeError, match="graph failed"):
                uc.execute(req)

    sandbox.release_environment.assert_called_once_with(execution_env)
    vcs.remove_session_worktree.assert_called_once_with("/repo", "sid-1")


def test_execute_removes_worktree_when_provision_fails(
    workspace_binding: WorkspaceBindingModel,
) -> None:
    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.side_effect = RuntimeError("no sandbox")

    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch("autonode.application.use_cases.run_workflow_uc.build_graph"):

            def registry_factory(env: ExecutionEnvironmentModel) -> ToolRegistryPort:
                return cast(ToolRegistryPort, MagicMock())

            def agent_factory_provider(path: str, registry: ToolRegistryPort) -> AgentFactoryPort:
                return cast(AgentFactoryPort, MagicMock())

            uc = RunWorkflowUseCase(
                vcs, sandbox, registry_factory, agent_factory_provider, checkpointer=MagicMock()
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id="sid-1",
            )
            with pytest.raises(RuntimeError, match="no sandbox"):
                uc.execute(req)

    sandbox.release_environment.assert_not_called()
    vcs.remove_session_worktree.assert_called_once_with("/repo", "sid-1")
