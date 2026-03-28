import uuid
from typing import Any

from autonode.application.use_cases.run_workflow_uc import (
    RunWorkflowUseCase,
    RunWorkflowUseCaseRequest,
    RunWorkflowUseCaseResponse,
)
from autonode.infrastructure.logging.session_logging import (
    attach_session_logging,
    detach_session_logging,
)
from autonode.presentation.workflow.models import WorkflowRunRequest


def run_workflow(
    use_case: RunWorkflowUseCase,
    raw_input: dict[str, Any],
) -> RunWorkflowUseCaseResponse:
    """Execute the workflow use case with the provided (injected) use_case instance."""
    validated = WorkflowRunRequest(**raw_input)
    thread_id = validated.thread_id if validated.thread_id else str(uuid.uuid4())

    autonode_logger, python_logger = attach_session_logging(thread_id)
    try:
        use_case_request = RunWorkflowUseCaseRequest(
            thread_id=thread_id,
            prompt=validated.prompt,
            workflow_path=validated.workflow_path,
            agents_path=validated.agents_path,
            repo_path=validated.repo_path,
            session_logger=autonode_logger,
            session_python_logger=python_logger,
        )
        return use_case.execute(use_case_request)
    finally:
        detach_session_logging(python_logger)
