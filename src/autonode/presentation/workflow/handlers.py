import uuid
from typing import Any, cast

from autonode.application.use_cases.run_workflow_uc import (
    RunWorkflowUseCase,
    RunWorkflowUseCaseRequest,
    RunWorkflowUseCaseResponse,
)
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.factory.agent_factory import LangChainAgentFactory
from autonode.infrastructure.sandbox.docker_adapter import DockerAdapter
from autonode.infrastructure.tools.registry import ToolRegistry
from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider
from autonode.presentation.workflow.models import WorkflowRunRequest


def run_workflow(raw_input: dict[str, Any]) -> RunWorkflowUseCaseResponse:
    validated = WorkflowRunRequest(**raw_input)
    thread_id = validated.thread_id or str(uuid.uuid4())

    use_case_request = RunWorkflowUseCaseRequest(
        thread_id=thread_id,
        prompt=validated.prompt,
        workflow_path=validated.workflow_path,
        agents_path=validated.agents_path,
        repo_path=validated.repo_path,
        no_cleanup=validated.no_cleanup,
    )

    vcs = GitWorktreeProvider()
    sandbox = DockerAdapter()

    def tool_registry_factory(env: ExecutionEnvironmentModel) -> ToolRegistryPort:
        return ToolRegistry(execution_env=env)

    def agent_factory_provider(path: str, registry: ToolRegistryPort) -> AgentFactoryPort:
        return LangChainAgentFactory(config_path=path, tool_registry=cast(ToolRegistry, registry))

    use_case = RunWorkflowUseCase(vcs, sandbox, tool_registry_factory, agent_factory_provider)
    return use_case.execute(use_case_request)
