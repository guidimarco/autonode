"""WorkflowYamlSchema, loader, and mapping to WorkflowModel."""

from pathlib import Path

import pytest

from autonode.infrastructure.config.loader import load_workflow_config
from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema


def test_workflow_yaml_schema_to_core() -> None:
    raw = {
        "version": 2,
        "factory": " dev_review_loop ",
        "max_iterations": 10,
        "token_budget": 500_000,
        "agents_path": "config/agents.yaml",
        "params": {"flag": True},
    }
    m = WorkflowYamlSchema.model_validate(raw).to_core()
    assert m.version == 2
    assert m.factory == "dev_review_loop"
    assert m.max_iterations == 10
    assert m.token_budget == 500_000
    assert m.agents_path == "config/agents.yaml"
    assert m.params == {"flag": True}


def test_load_workflow_config_from_testdata() -> None:
    path = Path(__file__).resolve().parent / "testdata" / "workflow_default.yaml"
    m = load_workflow_config(str(path))
    assert m.factory == "dev_review_loop"
    assert m.params["reviewer_structured"] is True


def test_schema_rejects_blank_factory() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        WorkflowYamlSchema.model_validate({"version": 2, "factory": "   "})


def test_schema_rejects_negative_budget() -> None:
    with pytest.raises(ValueError, match="token_budget"):
        WorkflowYamlSchema.model_validate({"version": 2, "factory": "x", "token_budget": -1})
