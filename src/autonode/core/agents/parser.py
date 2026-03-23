"""
Validate and normalize agent configuration dicts into AgentConfig.

Raises ValueError with actionable messages on invalid configuration.
"""

from __future__ import annotations

from autonode.core.agents.models import AgentModel


def parse_agents(agents: list[AgentModel]) -> list[AgentModel]:
    """
    Parse a list of dicts into a list of AgentConfig.

    Raises:
      ValueError: If the structure is invalid or missing required fields.
    """
    ids = [a.id for a in agents]
    if len(ids) != len(set(ids)):
        raise ValueError("There are agents with duplicate IDs in the configuration")
    return agents
