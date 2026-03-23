"""I file YAML di test devono vivere solo sotto tests/testdata/ (indipendenti da config/)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autonode.core.workflow import parse_workflow
from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema

TESTDATA = Path(__file__).resolve().parent / "testdata"
WORKFLOW_FIXTURE = TESTDATA / "workflow.yaml"


def test_testdata_workflow_yaml_parses() -> None:
    with WORKFLOW_FIXTURE.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, dict)
    cfg = parse_workflow(WorkflowYamlSchema.model_validate(raw).to_core())
    assert cfg.entry == "alpha"
    assert len(cfg.nodes) == 5
    assert len(cfg.post_processing) >= 1
    assert cfg.post_processing[0].action == "noop"


def test_workflow_schema_rejects_bad_version() -> None:
    with pytest.raises(ValidationError):
        WorkflowYamlSchema.model_validate(
            {
                "version": 2,
                "entry": "a",
                "nodes": [{"id": "a", "kind": "agent", "agent_id": "x"}],
            }
        )


def test_parse_workflow_rejects_missing_entry() -> None:
    raw = {
        "version": 1,
        "entry": "missing",
        "nodes": [{"id": "a", "kind": "agent", "agent_id": "alpha_agent"}],
        "edges": [],
        "routing": {},
    }
    with pytest.raises(ValueError, match="Entry node 'missing' not found in nodes"):
        parse_workflow(WorkflowYamlSchema.model_validate(raw).to_core())


def test_parse_workflow_rejects_unreachable_node() -> None:
    raw = {
        "version": 1,
        "entry": "a",
        "nodes": [
            {"id": "a", "kind": "agent", "agent_id": "alpha_agent"},
            {"id": "b", "kind": "state_update"},
        ],
        "edges": [],
        "routing": {},
    }
    with pytest.raises(ValueError, match="cannot reach node 'b'"):
        parse_workflow(WorkflowYamlSchema.model_validate(raw).to_core())


def test_parse_workflow_rejects_circular_graph_without_end() -> None:
    raw = {
        "version": 1,
        "entry": "a",
        "nodes": [
            {"id": "a", "kind": "agent", "agent_id": "alpha_agent"},
            {"id": "b", "kind": "state_update"},
        ],
        "edges": [
            {"from_node": "a", "to": "b"},
            {"from_node": "b", "to": "a"},
        ],
        "routing": {},
    }
    with pytest.raises(ValueError, match="cannot reach the end sentinel"):
        parse_workflow(WorkflowYamlSchema.model_validate(raw).to_core())
