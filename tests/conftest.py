"""Fixture: dati sotto tests/testdata/ letti solo con core + PyYAML (niente infrastructure)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from autonode.core.workflow import WorkflowModel, parse_workflow
from autonode.infrastructure.config.workflow_schema import WorkflowYamlSchema
from tests.stubs.agent_factory import StubAgentFactory

TESTDATA_DIR = Path(__file__).resolve().parent / "testdata"


def load_workflow_testdata() -> WorkflowModel:
    path = TESTDATA_DIR / "workflow.yaml"
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"workflow di test non è un mapping: {path}")
    return parse_workflow(WorkflowYamlSchema.model_validate(raw).to_core())


@pytest.fixture
def workflow_config() -> WorkflowModel:
    return load_workflow_testdata()


@pytest.fixture
def stub_agent_factory() -> StubAgentFactory:
    return StubAgentFactory()
