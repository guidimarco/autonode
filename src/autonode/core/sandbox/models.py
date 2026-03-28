"""
Sandbox core models (framework/infrastructure agnostic).
"""

from dataclasses import dataclass

from autonode.core.sandbox.session_paths import (
    outputs_host,
    session_root_host,
    worktree_host,
)

# Fixed paths in the container sandbox.
CONTAINER_WORKSPACE_PATH = "/workspace"
CONTAINER_OUTPUTS_PATH = "/outputs"


@dataclass(frozen=True, slots=True)
class WorkspaceBindingModel:
    """Host-side workspace binding prodotto dal provisioning VCS."""

    session_id: str
    repo_host_path: str
    branch_name: str

    @property
    def session_root_host_path(self) -> str:
        return session_root_host(self.repo_host_path, self.session_id)

    @property
    def worktree_host_path(self) -> str:
        return worktree_host(self.repo_host_path, self.session_id)

    @property
    def outputs_host_path(self) -> str:
        return outputs_host(self.repo_host_path, self.session_id)


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentModel:
    """
    Ambiente di esecuzione sessione: sandbox Docker e repo per risolvere i path host.

    I path worktree/output sul host sono sempre derivati da ``repo_host_path`` e ``session_id``.
    """

    session_id: str
    sandbox_id: str
    repo_host_path: str

    @property
    def session_root_host_path(self) -> str:
        return session_root_host(self.repo_host_path, self.session_id)

    @property
    def worktree_host_path(self) -> str:
        return worktree_host(self.repo_host_path, self.session_id)

    @property
    def outputs_host_path(self) -> str:
        return outputs_host(self.repo_host_path, self.session_id)
