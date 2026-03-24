"""Test del modello Pydantic `WorkflowRunRequest` (presentation layer)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from autonode.presentation.workflow.models import WorkflowRunRequest

TESTDATA = Path(__file__).resolve().parent / "testdata"


def _minimal_yaml_pair(tmp_path: Path) -> tuple[Path, Path]:
    workflow = tmp_path / "workflow.yaml"
    agents = tmp_path / "agents.yaml"
    workflow.write_text("entry: alpha\nnodes: []\n", encoding="utf-8")
    agents.write_text("agents: []\n", encoding="utf-8")
    return workflow, agents


def test_accepts_existing_paths(tmp_path: Path) -> None:
    wf, ag = _minimal_yaml_pair(tmp_path)
    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
    )
    assert req.workflow_path == str(wf)
    assert req.agents_path == str(ag)
    assert req.prompt == "hello world"


def test_rejects_missing_workflow_path(tmp_path: Path) -> None:
    wf, ag = _minimal_yaml_pair(tmp_path)
    missing_wf = tmp_path / "nope.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(missing_wf),
            agents_path=str(ag),
            prompt="hello world",
        )


def test_rejects_missing_agents_path(tmp_path: Path) -> None:
    wf, ag = _minimal_yaml_pair(tmp_path)
    missing_ag = tmp_path / "nope_agents.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(missing_ag),
            prompt="hello world",
        )


def test_prompt_too_short_raises() -> None:
    wf = TESTDATA / "workflow.yaml"
    ag = TESTDATA / "agents.yaml"
    with pytest.raises(ValidationError) as exc:
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(ag),
            prompt="1234",
        )
    errs = exc.value.errors()
    assert any(e.get("type") == "string_too_short" and e.get("loc") == ("prompt",) for e in errs)


def test_empty_prompt_uses_default(tmp_path: Path) -> None:
    wf, ag = _minimal_yaml_pair(tmp_path)
    req = WorkflowRunRequest.model_validate(
        {
            "workflow_path": str(wf),
            "agents_path": str(ag),
            "prompt": "",
        }
    )
    assert len(req.prompt) >= 5
    assert "Esplora la codebase" in req.prompt


def test_empty_workflow_path_uses_field_default(tmp_path: Path) -> None:
    _, ag = _minimal_yaml_pair(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workflow.yaml").write_text("entry: alpha\nnodes: []\n", encoding="utf-8")
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": "",
                "agents_path": str(ag),
                "prompt": "hello world",
            }
        )
    finally:
        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_none_workflow_path_uses_field_default(tmp_path: Path) -> None:
    _, ag = _minimal_yaml_pair(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workflow.yaml").write_text("entry: alpha\nnodes: []\n", encoding="utf-8")
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": None,
                "agents_path": str(ag),
                "prompt": "hello world",
            }
        )
    finally:
        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_accepts_testdata_yaml_paths() -> None:
    wf = TESTDATA / "workflow.yaml"
    ag = TESTDATA / "agents.yaml"
    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
    )
    assert Path(req.workflow_path).name == "workflow.yaml"
    assert Path(req.agents_path).name == "agents.yaml"
