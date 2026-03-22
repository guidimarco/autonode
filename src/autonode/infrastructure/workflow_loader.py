"""
Load workflow YAML from disk (infrastructure: I/O + format).

Parsing/validation lives in autonode.core.workflow.
"""

from pathlib import Path

import yaml

from autonode.core.workflow import WorkflowConfig, parse_workflow_config


def load_workflow_config(path: str = "config/workflow.yaml") -> WorkflowConfig:
    """Load and validate a workflow definition file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Workflow config non trovato: {path}")
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Workflow config deve essere un mapping YAML: {path}")
    return parse_workflow_config(raw)
