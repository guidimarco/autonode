"""
Validate and normalize agent configuration dicts into AgentConfig.

Raises ValueError with actionable messages on invalid configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from autonode.core.agents.models import AgentConfig

if TYPE_CHECKING:
    from autonode.infrastructure.tools.registry import ToolRegistry


def parse_agents_config(
    raw_list: Any, tool_registry: ToolRegistry | None = None
) -> list[AgentConfig]:
    """
    Parse a list of dicts into a list of AgentConfig.

    Raises:
      ValueError: If the structure is invalid or missing required fields.
    """
    if not isinstance(raw_list, list):
        raise ValueError("[parse_agents_config] The content must be a list of agents")

    adapter = TypeAdapter(list[AgentConfig])
    return adapter.validate_python(raw_list, context={"tool_registry": tool_registry})
