"""I file YAML di test devono vivere solo sotto tests/testdata/ (indipendenti da config/)."""

from __future__ import annotations

from pathlib import Path

import yaml

from autonode.core.workflow import parse_workflow_config

TESTDATA = Path(__file__).resolve().parent / "testdata"
WORKFLOW_FIXTURE = TESTDATA / "workflow.yaml"


def test_testdata_workflow_yaml_parses() -> None:
    with WORKFLOW_FIXTURE.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, dict)
    cfg = parse_workflow_config(raw)
    assert cfg.entry == "alpha"
    assert len(cfg.nodes) == 5
    assert len(cfg.post_processing) >= 1
    assert cfg.post_processing[0].action == "noop"
