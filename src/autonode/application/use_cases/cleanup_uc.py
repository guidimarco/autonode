from dataclasses import dataclass

from autonode.core.sandbox.ports import SandboxProviderPort
from autonode.core.workflow.ports import VCSProviderPort


@dataclass(frozen=True, slots=True)
class CleanupUseCaseRequest:
    repo_path: str
    session_id: str | None = None
    delete_branch: bool = False


class CleanupSessionsUseCase:

    def __init__(
        self,
        vcs: VCSProviderPort,
        sandbox: SandboxProviderPort,
    ):
        self.vcs = vcs
        self.sandbox = sandbox

    def execute(self, request: CleanupUseCaseRequest) -> None:
        if request.session_id:
            self.vcs.remove_session_worktree(request.session_id, request.repo_path)
            self.sandbox.remove_session_sandbox(request.session_id)
            if request.delete_branch:
                self.vcs.delete_session_branch(request.repo_path, request.session_id)
        else:
            self.vcs.remove_all_session_worktrees(request.repo_path)
            self.sandbox.remove_all_session_sandboxes()
            if request.delete_branch:
                self.vcs.delete_all_session_branches(request.repo_path)
