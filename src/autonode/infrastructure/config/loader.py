"""
Load workflow YAML from disk (infrastructure: I/O + format).

Parsing/validation boundary lives in infrastructure schemas.
"""

from pathlib import Path

import yaml

from autonode.core.agents.models import AgentModel
from autonode.core.constants import DEFAULT_AGENTS_CONFIG_PATH, DEFAULT_WORKFLOW_CONFIG_PATH
from autonode.core.workflow import WorkflowModel
from autonode.infrastructure.config.agents_schema import AgentsYamlSchema
from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema


def load_agents_config(config_path: str = DEFAULT_AGENTS_CONFIG_PATH) -> dict[str, AgentModel]:
    """Load agents from YAML; returns dict agent_id -> AgentModel."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configurazione degli agenti non trovata: {config_path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    schema = AgentsYamlSchema.model_validate(data or {})
    return schema.to_core()


def load_workflow_config(path: str = DEFAULT_WORKFLOW_CONFIG_PATH) -> WorkflowModel:
    """Load and validate a workflow definition file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Workflow config non trovato: {path}")
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Workflow config deve essere un mapping YAML: {path}")
    return WorkflowYamlSchema.model_validate(raw).to_core()
