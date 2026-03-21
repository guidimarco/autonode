"""
Domain and configuration models. Framework-agnostic.
"""

from typing import NotRequired, TypedDict


class AgentConfig(TypedDict):
    """Configuration for a single agent (from config/agents.yaml)."""

    id: str
    name: str
    model: str
    temperature: float
    tools: list[str]
    role: NotRequired[str]
    system_prompt: NotRequired[str]
