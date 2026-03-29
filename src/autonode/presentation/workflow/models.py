from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from autonode.core.constants import DEFAULT_AGENTS_CONFIG_PATH, DEFAULT_WORKFLOW_CONFIG_PATH
from autonode.infrastructure.paths.repo_resolution import ensure_git_repo_under_root

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PROJECT_CONFIG_ROOT = _PROJECT_ROOT / "config"


class WorkflowRunRequest(BaseModel):
    """
    Request model for running a workflow.
    """

    workflow_path: str = Field(
        default=DEFAULT_WORKFLOW_CONFIG_PATH,
        description="The path to the workflow YAML configuration file.",
    )
    agents_path: str = Field(
        default=DEFAULT_AGENTS_CONFIG_PATH,
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
        description="Root Git sotto REPOS_ROOT: path relativo o assoluto entro la stessa radice.",
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
    def _validate_path_with_config_boundary(cls, v: str) -> str:
        # Real validation (config boundary enforcement) is done in `validate_config_paths`.
        # This legacy validator is kept as a lightweight placeholder.
        return v

    @field_validator("repo_path")
    @classmethod
    def is_git_repo(cls, v: str) -> str:
        path = ensure_git_repo_under_root(v)
        if not path.is_dir():
            raise ValueError(f"The path {v} does not exist.")
        if not (path / ".git").exists():
            raise ValueError(f"The path {v} is not a Git repository.")
        return str(path)

    @model_validator(mode="after")
    def validate_config_paths(self) -> "WorkflowRunRequest":
        """
        Security: only allow `workflow_path` and `agents_path` YAML files under `config/`.

        Allowed roots:
        - this project's `<PROJECT_ROOT>/config`
        - target git repo's `<repo_path>/config`
        """

        def _to_candidate(path_str: str) -> Path:
            # Resolve relative paths against the current working directory: we validate what
            # will actually be read by `load_*_config(path_str)` later.
            return Path(path_str).expanduser().resolve()

        allowed_roots = [
            _PROJECT_CONFIG_ROOT,
            Path(self.repo_path).resolve() / "config",
        ]

        for field_name in ("workflow_path", "agents_path"):
            candidate = _to_candidate(getattr(self, field_name))

            if not candidate.exists() or not candidate.is_file():
                raise ValueError(f"Invalid {field_name}: file does not exist: {candidate}")

            ok = False
            for root in allowed_roots:
                try:
                    candidate.relative_to(root)
                    ok = True
                    break
                except ValueError:
                    continue

            if not ok:
                raise ValueError(
                    f"Invalid {field_name}: only files under config/ are allowed "
                    f"(got {candidate})."
                )

        return self
