import os

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

    @field_validator("workflow_path", "agents_path", "prompt", mode="before")
    @classmethod
    def set_default_if_none(cls, v: str | None, info: ValidationInfo) -> str:
        if v is None or v == "":
            field_name = info.field_name
            if field_name is None:
                raise ValueError(f"The field {info.field_name} is missing.")
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
