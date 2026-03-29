"""
Workflow configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; factories build runtime topology in code.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from autonode.core.constants import DEFAULT_AGENTS_CONFIG_PATH, DEFAULT_TOKEN_BUDGET

# ── Post-workflow actions ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PostProcessStepModel:
    """Declarative post-workflow action (handled by post_processing runner)."""

    action: str
    params: dict[str, Any] = field(default_factory=dict)


# ── Workflow model ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WorkflowModel:
    """Factory selector model: topology lives in Python factories."""

    version: Literal[2] = 2
    factory: str = ""
    max_iterations: int = 3
    token_budget: int = DEFAULT_TOKEN_BUDGET
    agents_path: str = DEFAULT_AGENTS_CONFIG_PATH
    params: dict[str, Any] = field(default_factory=dict)
    post_processing: list[PostProcessStepModel] = field(default_factory=list)
