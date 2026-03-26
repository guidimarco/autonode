from typing import Any

from autonode.application.use_cases.cleanup_uc import CleanupSessionsUseCase, CleanupUseCaseRequest
from autonode.presentation.cleanup.models import CleanupRequest


def run_cleanup(use_case: CleanupSessionsUseCase, raw_input: dict[str, Any]) -> None:
    validated = CleanupRequest(**raw_input)

    use_case_request = CleanupUseCaseRequest(
        repo_path=validated.repo_path,
        session_id=validated.session_id,
        delete_branch=validated.delete_branch,
    )

    use_case.execute(use_case_request)
