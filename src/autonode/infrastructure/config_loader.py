"""
Load agent configuration from YAML. Infrastructure: file I/O and config format.
"""

from pathlib import Path

import yaml

from autonode.core.agents.models import AgentConfig


def load_agents_config(config_path: str = "config/agents.yaml") -> dict[str, AgentConfig]:
    """Load agents from YAML; returns dict agent_id -> AgentConfig."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configurazione degli agenti non trovata: {config_path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    agents = data.get("agents", [])
    return {agent["id"]: AgentConfig(**agent) for agent in agents if "id" in agent}
