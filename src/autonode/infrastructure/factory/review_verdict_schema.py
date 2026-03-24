"""
Pydantic schema for reviewer structured output (infrastructure boundary).

Maps validated LLM output to core ReviewVerdictModel via to_core().
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autonode.core.agents.models import ReviewVerdictModel


class ReviewVerdictSchema(BaseModel):
    """Shape of reviewer structured output as returned by the LLM adapter."""

    model_config = ConfigDict(frozen=True)

    is_approved: bool
    feedback: str
    missing_requirements: list[str] = Field(default_factory=list)

    def to_core(self) -> ReviewVerdictModel:
        return ReviewVerdictModel(
            is_approved=self.is_approved,
            feedback=self.feedback,
            missing_requirements=list(self.missing_requirements),
        )
