import os
from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class WorkflowRunRequest(BaseModel):
    """
    Request model for running a workflow.
    """

    workflow_path: str = Field(
        default="config/workflow.yaml",
        description="The path to the workflow YAML configuration file.",
    )
    agents_path: str = Field(
        default="config/agents.yaml",
        description="The path to the agents YAML configuration file.",
    )
    prompt: str = Field(
        default=(
            "Esplora la codebase e identifica dove sono definite le interfacce (Port) "
            "per il sistema di controllo versione (VCS)."
            "Una volta trovato il file, aggiungi un commento in cima al file spiegando "
            "brevemente quali classi lo implementano effettivamente nel layer dell'infrastruttura."
        ),
        min_length=5,
        description="The prompt to run the workflow with.",
    )
    repo_path: str = Field(
        default=".",
        description="Git root repository path (directory that contains .git).",
    )
    thread_id: str | None = Field(
        default=None,
        description="Stable id for worktree/session; generated if omitted.",
    )

    @field_validator("workflow_path", "agents_path", "prompt", mode="before")
    @classmethod
    def set_default_if_none(cls, v: str | None, info: ValidationInfo) -> str:
        if v is None or v == "":
            field_name = info.field_name
            assert field_name is not None
            field = cls.model_fields.get(field_name)
            if field and field.default is not None:
                return str(field.default)
            raise ValueError(f"The field {field_name} is required and has no default value.")
        return v

    @field_validator("workflow_path", "agents_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not os.path.exists(v):
            raise ValueError(f"The path {v} does not exist.")
        return v

    @field_validator("repo_path")
    @classmethod
    def is_git_repo(cls, v: str) -> str:
        path = Path(v)
        if not path.is_dir():
            raise ValueError(f"The path {v} does not exist.")
        if not (path / ".git").exists():
            raise ValueError(f"The path {v} is not a Git repository.")
        return v
