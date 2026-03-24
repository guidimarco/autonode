"""
Agent configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; validated when building the graph.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AgentModel:
    """Pure core DTO for agent configuration."""

    id: str
    model: str
    name: str | None = None
    temperature: float = 0.0
    tools: list[str] = field(default_factory=list)
    role: str | None = None
    system_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewVerdictModel:
    """Structured reviewer outcome (routing + feedback), framework-agnostic."""

    is_approved: bool
    feedback: str
    missing_requirements: list[str] = field(default_factory=list)
