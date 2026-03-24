from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class CleanupRequest(BaseModel):
    """
    Request model for running a workflow.
    """

    repo_path: str = Field(
        default=".",
        description="Git root repository path (directory that contains .git).",
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
        path = Path(v)
        if not path.is_dir():
            raise ValueError(f"The path {v} does not exist.")
        if not (path / ".git").exists():
            raise ValueError(f"The path {v} is not a Git repository.")
        return v
