from typing import Any

from autonode.application.use_cases.cleanup_uc import CleanupSessionsUseCase, CleanupUseCaseRequest
from autonode.infrastructure.sandbox.docker_adapter import DockerAdapter
from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider
from autonode.presentation.cleanup.models import CleanupRequest


def run_cleanup(raw_input: dict[str, Any]) -> None:
    validated = CleanupRequest(**raw_input)

    use_case_request = CleanupUseCaseRequest(
        repo_path=validated.repo_path,
        session_id=validated.session_id,
        delete_branch=validated.delete_branch,
    )

    vcs = GitWorktreeProvider()
    sandbox = DockerAdapter()

    use_case = CleanupSessionsUseCase(vcs, sandbox)
    use_case.execute(use_case_request)
