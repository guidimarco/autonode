from __future__ import annotations

import pytest

from autonode.core.agents.parser import parse_agents
from autonode.infrastructure.config.agents_schema import AgentsYamlSchema


def test_parse_agents_accepts_unique_ids() -> None:
    schema = AgentsYamlSchema.model_validate(
        {
            "agents": [
                {"id": "alpha", "model": "openrouter/a"},
                {"id": "beta", "model": "openrouter/b"},
            ]
        }
    )
    agents = list(schema.to_core().values())
    parsed = parse_agents(agents)
    assert len(parsed) == 2
    assert {a.id for a in parsed} == {"alpha", "beta"}


def test_parse_agents_rejects_duplicate_ids() -> None:
    schema = AgentsYamlSchema.model_validate(
        {
            "agents": [
                {"id": "dup", "model": "openrouter/a"},
                {"id": "dup", "model": "openrouter/b"},
            ]
        }
    )
    # Keep duplicates by extracting from the schema list directly.
    duplicated = [item.to_core() for item in schema.agents]
    with pytest.raises(ValueError, match="duplicate IDs"):
        parse_agents(duplicated)
