import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from autonode.application.workflow.builder import build_graph
from autonode.application.workflow.state import make_initial_graph_state
from autonode.core.agents.models import ReviewVerdictModel
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.sandbox.ports import SandboxProviderPort
from autonode.core.tools.ports import ToolRegistryPort
from autonode.core.workflow.ports import VCSProviderPort
from autonode.infrastructure.config.loader import load_workflow_config


@dataclass(frozen=True, slots=True)
class RunWorkflowUseCaseRequest:
    thread_id: str
    prompt: str
    workflow_path: str
    agents_path: str
    repo_path: str
    no_cleanup: bool = False


@dataclass(frozen=True, slots=True)
class RunWorkflowUseCaseResponse:
    """Completed workflow: ``verdict`` is ``approved`` or ``revision`` (from ``review_verdict``)."""

    session_id: str
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
        tool_registry_factory: Callable[[ExecutionEnvironmentModel], ToolRegistryPort],
        agent_factory_provider: Callable[[str, ToolRegistryPort], AgentFactoryPort],
    ):
        self.vcs = vcs_provider
        self.sandbox = sandbox_provider
        self.tool_registry_factory = tool_registry_factory
        self.agent_factory_provider = agent_factory_provider

    def execute(self, request: RunWorkflowUseCaseRequest) -> RunWorkflowUseCaseResponse:

        workspace = self.vcs.setup_session_worktree(request.thread_id, request.repo_path)
        execution_env = self.sandbox.provision_environment(workspace)

        try:
            registry = self.tool_registry_factory(execution_env)
            factory = self.agent_factory_provider(request.agents_path, registry)

            workflow = load_workflow_config(request.workflow_path)
            graph = build_graph(workflow, factory, registry, vcs_provider=self.vcs)

            initial_state = make_initial_graph_state(
                request.prompt,
                execution_env=execution_env,
                workspace=workspace,
            )
            final_state = graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": request.thread_id}},
            )
            last_msg = final_state["messages"][-1]
            content = getattr(last_msg, "content", str(last_msg))

            rv = final_state["review_verdict"]
            verdict_label = "approved" if rv.is_approved else "revision"
            return RunWorkflowUseCaseResponse(
                session_id=workspace.session_id,
                verdict=verdict_label,
                review_verdict=rv,
                iteration=final_state["iteration"],
                final_output=content,
                last_commit_hash=final_state.get("last_commit_hash", ""),
            )
        finally:
            if not request.no_cleanup:
                self.sandbox.release_environment(execution_env)
