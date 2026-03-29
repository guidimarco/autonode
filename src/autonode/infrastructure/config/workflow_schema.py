"""
Pydantic schemas for external configuration inputs.

Validation happens at the infrastructure boundary, then data is mapped to pure
core dataclasses via `to_core()`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autonode.core.constants import DEFAULT_AGENTS_CONFIG_PATH, DEFAULT_TOKEN_BUDGET
from autonode.core.workflow.models import PostProcessStepModel, WorkflowModel


class PostProcessStepYamlSchema(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)

    def to_core(self) -> PostProcessStepModel:
        return PostProcessStepModel(self.action, dict(self.params))


class WorkflowYamlSchema(BaseModel):
    """Factory-driven workflow selector schema."""

    version: Literal[2] = 2
    factory: str = Field(..., min_length=1)
    max_iterations: int = Field(default=3, ge=0)
    token_budget: int = Field(default=DEFAULT_TOKEN_BUDGET, ge=0)
    agents_path: str = Field(default=DEFAULT_AGENTS_CONFIG_PATH, min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    post_processing: list[PostProcessStepYamlSchema] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("factory", "agents_path")
    @classmethod
    def _strip_non_empty_strings(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace-only")
        return s

    def to_core(self) -> WorkflowModel:
        return WorkflowModel(
            version=2,
            factory=self.factory.strip(),
            max_iterations=self.max_iterations,
            token_budget=self.token_budget,
            agents_path=self.agents_path.strip(),
            params=dict(self.params),
            post_processing=[step.to_core() for step in self.post_processing],
        )
