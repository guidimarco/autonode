"""
Sandbox core models (framework/infrastructure agnostic).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkspaceBindingModel:
    """Host-side workspace binding produced by VCS provisioning."""

    session_id: str
    repo_host_path: str
    worktree_host_path: str
    branch_name: str


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentModel:
    """
    Ambiente di esecuzione sessione: path host lato worktree e root nel container.

    I tool devono usare solo ``worktree_host_path`` (host) e ``container_workspace_path``
    (comandi nel container), non la root della repo originale.
    """

    session_id: str
    sandbox_id: str
    worktree_host_path: str
    container_workspace_path: str
