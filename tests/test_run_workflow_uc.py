"""RunWorkflowUseCase: cleanup deterministico e risposta con branch di sessione."""

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
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
from autonode.core.logging import AutonodeLogger
from autonode.core.sandbox.models import ExecutionEnvironmentModel, WorkspaceBindingModel
from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.logging.session_logging import (
    attach_session_logging,
    detach_session_logging,
)

_SID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture(autouse=True)
def _fake_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dr = tmp_path / "data"
    dr.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.DATA_ROOT", str(dr))


@pytest.fixture
def session_loggers() -> Generator[tuple[AutonodeLogger, logging.Logger], None, None]:
    autonode_log, py_log = attach_session_logging(_SID)
    yield autonode_log, py_log
    detach_session_logging(py_log)


@pytest.fixture
def workspace_binding() -> WorkspaceBindingModel:
    return WorkspaceBindingModel(
        session_id=_SID,
        repo_host_path="/repo",
        branch_name=f"autonode/session-{_SID[:80]}",
    )


@pytest.fixture
def execution_env(workspace_binding: WorkspaceBindingModel) -> ExecutionEnvironmentModel:
    return ExecutionEnvironmentModel(
        session_id=workspace_binding.session_id,
        sandbox_id="container-abc",
        repo_host_path=workspace_binding.repo_host_path,
    )


def test_execute_releases_container_then_removes_worktree(
    workspace_binding: WorkspaceBindingModel,
    execution_env: ExecutionEnvironmentModel,
    session_loggers: tuple[AutonodeLogger, logging.Logger],
) -> None:
    events: list[str] = []

    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.return_value = execution_env
    sandbox.release_environment.side_effect = lambda env: events.append("release")
    vcs.remove_session_worktree.side_effect = lambda sid, rp: events.append("remove")

    def registry_factory(
        env: ExecutionEnvironmentModel,
        session_logger: AutonodeLogger,
    ) -> ToolRegistryPort:
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

    autonode_log, py_log = session_loggers
    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch(
            "autonode.application.use_cases.run_workflow_uc.build_graph",
            return_value=graph,
        ):
            uc = RunWorkflowUseCase(
                vcs,
                sandbox,
                registry_factory,
                agent_factory_provider,
                checkpointer=MagicMock(),
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id=_SID,
                session_logger=autonode_log,
                session_python_logger=py_log,
            )
            out = uc.execute(req)

    assert out.branch_name == workspace_binding.branch_name
    assert events == ["release", "remove"]
    sandbox.release_environment.assert_called_once_with(execution_env)
    sandbox.provision_environment.assert_called_once()
    pc = sandbox.provision_environment.call_args
    assert pc.kwargs["session_python_logger"] is py_log
    vcs.remove_session_worktree.assert_called_once_with(_SID, "/repo")
    vcs.delete_session_branch.assert_not_called()


def test_execute_cleanup_after_graph_raises(
    workspace_binding: WorkspaceBindingModel,
    execution_env: ExecutionEnvironmentModel,
    session_loggers: tuple[AutonodeLogger, logging.Logger],
) -> None:
    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.return_value = execution_env

    graph = MagicMock()
    graph.invoke.side_effect = RuntimeError("graph failed")

    autonode_log, py_log = session_loggers
    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch(
            "autonode.application.use_cases.run_workflow_uc.build_graph",
            return_value=graph,
        ):

            def registry_factory(
                env: ExecutionEnvironmentModel,
                session_logger: AutonodeLogger,
            ) -> ToolRegistryPort:
                return cast(ToolRegistryPort, MagicMock())

            def agent_factory_provider(
                path: str,
                registry: ToolRegistryPort,
            ) -> AgentFactoryPort:
                return cast(AgentFactoryPort, MagicMock())

            uc = RunWorkflowUseCase(
                vcs,
                sandbox,
                registry_factory,
                agent_factory_provider,
                checkpointer=MagicMock(),
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id=_SID,
                session_logger=autonode_log,
                session_python_logger=py_log,
            )
            with pytest.raises(RuntimeError, match="graph failed"):
                uc.execute(req)

    sandbox.release_environment.assert_called_once_with(execution_env)
    vcs.remove_session_worktree.assert_called_once_with(_SID, "/repo")


def test_execute_removes_worktree_when_provision_fails(
    workspace_binding: WorkspaceBindingModel,
    session_loggers: tuple[AutonodeLogger, logging.Logger],
) -> None:
    vcs = MagicMock()
    vcs.setup_session_worktree.return_value = workspace_binding
    sandbox = MagicMock()
    sandbox.provision_environment.side_effect = RuntimeError("no sandbox")

    autonode_log, py_log = session_loggers
    with patch(
        "autonode.application.use_cases.run_workflow_uc.load_workflow_config",
        return_value=MagicMock(),
    ):
        with patch("autonode.application.use_cases.run_workflow_uc.build_graph"):

            def registry_factory(
                env: ExecutionEnvironmentModel,
                session_logger: AutonodeLogger,
            ) -> ToolRegistryPort:
                return cast(ToolRegistryPort, MagicMock())

            def agent_factory_provider(
                path: str,
                registry: ToolRegistryPort,
            ) -> AgentFactoryPort:
                return cast(AgentFactoryPort, MagicMock())

            uc = RunWorkflowUseCase(
                vcs,
                sandbox,
                registry_factory,
                agent_factory_provider,
                checkpointer=MagicMock(),
            )
            req = RunWorkflowUseCaseRequest(
                prompt="hello world task",
                workflow_path="/w.yaml",
                agents_path="/a.yaml",
                repo_path="/repo",
                thread_id=_SID,
                session_logger=autonode_log,
                session_python_logger=py_log,
            )
            with pytest.raises(RuntimeError, match="no sandbox"):
                uc.execute(req)

    sandbox.release_environment.assert_not_called()
    vcs.remove_session_worktree.assert_called_once_with(_SID, "/repo")
