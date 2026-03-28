"""
Sandbox core models (framework/infrastructure agnostic).
"""

from dataclasses import dataclass

from autonode.core.sandbox.session_paths import (
    session_op_root,
    session_outputs_path,
    session_workspace_path,
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
    def session_op_root_path(self) -> str:
        return session_op_root(self.session_id)

    @property
    def worktree_host_path(self) -> str:
        return session_workspace_path(self.session_id)

    @property
    def outputs_host_path(self) -> str:
        return session_outputs_path(self.session_id)


@dataclass(frozen=True, slots=True)
class ExecutionEnvironmentModel:
    """
    Ambiente di esecuzione sessione: sandbox Docker e repo per contesto Git su host.

    I path worktree/output sul host derivano solo da ``session_id`` (layout operativo sotto
    ``{REPOS_ROOT}/autonode_docker/``).
    """

    session_id: str
    sandbox_id: str
    repo_host_path: str

    @property
    def session_op_root_path(self) -> str:
        return session_op_root(self.session_id)

    @property
    def worktree_host_path(self) -> str:
        return session_workspace_path(self.session_id)

    @property
    def outputs_host_path(self) -> str:
        return session_outputs_path(self.session_id)
