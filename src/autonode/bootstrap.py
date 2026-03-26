from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from autonode.application.use_cases.cleanup_uc import CleanupSessionsUseCase
from autonode.application.use_cases.run_workflow_uc import RunWorkflowUseCase
from autonode.core.agents.ports import AgentFactoryPort
from autonode.core.sandbox.models import ExecutionEnvironmentModel
from autonode.core.tools.ports import ToolRegistryPort
from autonode.infrastructure.factory.agent_factory import LangChainAgentFactory
from autonode.infrastructure.persistence.sqlite_manager import SqliteCheckpointManager
from autonode.infrastructure.sandbox.docker_adapter import DockerAdapter
from autonode.infrastructure.tools.registry import ToolRegistry
from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider


@dataclass
class AppContainer:
    """
    Container of singletons and use cases.
    """

    checkpoint_manager: Any
    run_workflow_use_case: RunWorkflowUseCase
    cleanup_use_case: CleanupSessionsUseCase


def bootstrap_app() -> AppContainer:
    """
    Bootstrap the application container.
    One time only.
    """
    # 1. Infrastructure: Singleton
    db_path = os.environ.get("AUTONODE_DB_PATH", "./autonode.db")
    cp_manager = SqliteCheckpointManager(db_path=Path(db_path))
    # ^ ^ ^ Singleton SQLite checkpoint manager: open the connection once per process
    vcs = GitWorktreeProvider()
    sandbox = DockerAdapter()

    # 2. Factories: Tool Registry and Agent Factory
    def tool_registry_factory(env: ExecutionEnvironmentModel) -> ToolRegistryPort:
        return ToolRegistry(execution_env=env)

    def agent_factory_provider(path: str, registry: ToolRegistryPort) -> AgentFactoryPort:
        return LangChainAgentFactory(
            config_path=path,
            tool_registry=cast(ToolRegistry, registry),
        )

    # 3. Application: Use Cases
    run_workflow_use_case = RunWorkflowUseCase(
        vcs_provider=vcs,
        sandbox_provider=sandbox,
        tool_registry_factory=tool_registry_factory,
        agent_factory_provider=agent_factory_provider,
        checkpointer=cp_manager.checkpointer,
    )

    cleanup_use_case = CleanupSessionsUseCase(
        vcs=vcs,
        sandbox=sandbox,
    )

    return AppContainer(
        checkpoint_manager=cp_manager,
        run_workflow_use_case=run_workflow_use_case,
        cleanup_use_case=cleanup_use_case,
    )
