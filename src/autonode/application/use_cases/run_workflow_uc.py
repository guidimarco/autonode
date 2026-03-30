import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver

from autonode.application.workflow.factories import FactoryContext, get_registered_factory
from autonode.application.workflow.state import make_initial_graph_state
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.exceptions import TokenBudgetExceededError
from autonode.core.logging import AutonodeLogger
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.sandbox.ports import SandboxProviderPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.ports import VCSProviderPort
from autonode.infrastructure.config.loader import load_workflow_config
from autonode.infrastructure.persistence.session_status_store import write_session_status
from autonode.infrastructure.telemetry import TokenBudgetCallback, TokenBudgetExceeded


@dataclass(frozen=True, slots=True)
class RunWorkflowUseCaseRequest:
    prompt: str
    workflow_path: str
    agents_path: str
    repo_path: str
    session_logger: AutonodeLogger
    session_python_logger: logging.Logger
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True, slots=True)
class RunWorkflowUseCaseResponse:
    """Completed workflow: ``verdict`` is ``approved`` or ``revision`` (from ``review_verdict``)."""

    session_id: str
    branch_name: str
    verdict: str
    review_verdict: ReviewVerdictModel
    iteration: int
    final_output: str
    last_commit_hash: str


class RunWorkflowUseCase:

    def __init__(
        self,
        vcs_provider: VCSProviderPort,
        sandbox_provider: SandboxProviderPort,
        tool_registry_factory: Callable[
            [ExecutionEnvironmentModel, AutonodeLogger], ToolRegistryPort
        ],
        agent_factory_provider: Callable[[str, ToolRegistryPort], AgentFactoryPort],
        checkpointer: BaseCheckpointSaver[Any],
    ):
        self.vcs = vcs_provider
        self.sandbox = sandbox_provider
        self.tool_registry_factory = tool_registry_factory
        self.agent_factory_provider = agent_factory_provider
        self.checkpointer = checkpointer

    def execute(self, request: RunWorkflowUseCaseRequest) -> RunWorkflowUseCaseResponse:
        workspace = None
        execution_env = None
        try:
            workspace = self.vcs.setup_session_worktree(request.thread_id, request.repo_path)
            write_session_status(
                workspace.session_id,
                {
                    "status": "running",
                    "repo_path": request.repo_path,
                    "started_at": datetime.now(UTC).isoformat(),
                },
            )
            execution_env = self.sandbox.provision_environment(
                workspace,
                session_python_logger=request.session_python_logger,
            )
            registry = self.tool_registry_factory(execution_env, request.session_logger)
            factory = self.agent_factory_provider(request.agents_path, registry)

            workflow = load_workflow_config(request.workflow_path)
            factory_fn = get_registered_factory(workflow.factory)
            graph = factory_fn(
                FactoryContext(
                    workflow=workflow,
                    agent_factory=factory,
                    tool_registry=registry,
                    vcs_provider=self.vcs,
                    checkpointer=self.checkpointer,
                    session_python_logger=request.session_python_logger,
                )
            )
            token_callback = TokenBudgetCallback(budget=workflow.token_budget)

            initial_state = make_initial_graph_state(
                request.prompt,
                execution_env=execution_env,
                workspace=workspace,
                token_budget=workflow.token_budget,
            )
            try:
                final_state = graph.invoke(
                    initial_state,
                    config={
                        "configurable": {"thread_id": request.thread_id},
                        "callbacks": [token_callback],
                    },
                )
            except TokenBudgetExceeded as exc:
                raise TokenBudgetExceededError(exc.total_tokens, exc.budget) from exc
            last_msg = final_state["messages"][-1]
            content = getattr(last_msg, "content", str(last_msg))

            rv = final_state["review_verdict"]
            verdict_label = "approved" if rv.is_approved else "revision"
            write_session_status(
                workspace.session_id,
                {
                    "status": "completed",
                    "verdict": verdict_label,
                    "branch_name": workspace.branch_name,
                    "iteration": final_state["iteration"],
                    "finished_at": datetime.now(UTC).isoformat(),
                },
            )
            return RunWorkflowUseCaseResponse(
                session_id=workspace.session_id,
                branch_name=workspace.branch_name,
                verdict=verdict_label,
                review_verdict=rv,
                iteration=final_state["iteration"],
                final_output=content,
                last_commit_hash=final_state.get("last_commit_hash", ""),
            )
        except Exception as exc:
            sid = workspace.session_id if workspace is not None else request.thread_id
            write_session_status(
                sid,
                {
                    "status": "failed",
                    "error": str(exc),
                    "finished_at": datetime.now(UTC).isoformat(),
                },
            )
            raise
        finally:
            if execution_env is not None:
                self.sandbox.release_environment(execution_env)
            if workspace is not None:
                self.vcs.remove_session_worktree(workspace.session_id, request.repo_path)
