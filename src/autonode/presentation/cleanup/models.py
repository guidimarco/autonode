from pydantic import BaseModel, Field, field_validator

from autonode.infrastructure.paths.repo_resolution import ensure_git_repo_under_root


class CleanupRequest(BaseModel):
    """
    Request model for running a workflow.
    """

    repo_path: str = Field(
        default=".",
        description="Root Git sotto REPOS_ROOT: path relativo o assoluto entro la stessa radice.",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID.",
    )
    delete_branch: bool = Field(
        default=False,
        description="Whether to delete the branch after the cleanup.",
    )

    @field_validator("repo_path")
    @classmethod
    def is_git_repo(cls, v: str) -> str:
        path = ensure_git_repo_under_root(v)
        if not path.is_dir():
            raise ValueError(f"The path {v} does not exist.")
        if not (path / ".git").exists():
            raise ValueError(f"The path {v} is not a Git repository.")
        return str(path)
