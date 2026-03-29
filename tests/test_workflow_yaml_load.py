"""I file YAML di test devono vivere solo sotto tests/testdata/ (indipendenti da config/)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema

TESTDATA = Path(__file__).resolve().parent / "testdata"
WORKFLOW_FIXTURE = TESTDATA / "workflow_default.yaml"


def test_testdata_workflow_yaml_parses() -> None:
    with WORKFLOW_FIXTURE.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, dict)
    cfg = WorkflowYamlSchema.model_validate(raw).to_core()
    assert cfg.factory == "dev_review_loop"
    assert cfg.max_iterations == 10
    assert cfg.token_budget == 500_000
    assert cfg.params["reviewer_structured"] is True


def test_workflow_schema_rejects_bad_version() -> None:
    with pytest.raises(ValidationError):
        WorkflowYamlSchema.model_validate(
            {
                "version": 1,
                "factory": "dev_review_loop",
            }
        )


def test_workflow_schema_rejects_legacy_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WorkflowYamlSchema.model_validate(
            {
                "version": 2,
                "factory": "dev_review_loop",
                "entry": "legacy",
            }
        )
