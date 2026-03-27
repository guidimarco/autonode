"""Test del modello Pydantic `WorkflowRunRequest` (presentation layer)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autonode.presentation.workflow.models import WorkflowRunRequest

TESTDATA = Path(__file__).resolve().parent / "testdata"


def _minimal_git_repo_with_config(tmp_path: Path) -> tuple[Path, Path]:
    """
    Create a minimal git repo root for validation:
    - `tmp_path/.git/` exists (repo_path validator)
    - `tmp_path/config/` contains workflow + agents YAMLs (config-only validator)
    """
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    workflow = config_dir / "workflow.yaml"
    agents = config_dir / "agents.yaml"
    workflow.write_text("entry: alpha\nnodes: []\n", encoding="utf-8")
    agents.write_text("agents: []\n", encoding="utf-8")
    return workflow, agents


def test_accepts_existing_paths(tmp_path: Path) -> None:
    wf, ag = _minimal_git_repo_with_config(tmp_path)
    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
        repo_path=str(tmp_path),
    )
    assert req.workflow_path == str(wf)
    assert req.agents_path == str(ag)
    assert req.prompt == "hello world"


def test_rejects_missing_workflow_path(tmp_path: Path) -> None:
    _, ag = _minimal_git_repo_with_config(tmp_path)
    missing_wf = tmp_path / "config" / "nope.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(missing_wf),
            agents_path=str(ag),
            prompt="hello world",
            repo_path=str(tmp_path),
        )


def test_rejects_missing_agents_path(tmp_path: Path) -> None:
    wf, _ = _minimal_git_repo_with_config(tmp_path)
    missing_ag = tmp_path / "config" / "nope_agents.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(missing_ag),
            prompt="hello world",
            repo_path=str(tmp_path),
        )


def test_prompt_too_short_raises(tmp_path: Path) -> None:
    wf, ag = _minimal_git_repo_with_config(tmp_path)
    with pytest.raises(ValidationError) as exc:
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(ag),
            prompt="1234",
            repo_path=str(tmp_path),
        )
    errs = exc.value.errors()
    assert any(e.get("type") == "string_too_short" and e.get("loc") == ("prompt",) for e in errs)


def test_empty_prompt_uses_default(tmp_path: Path) -> None:
    wf, ag = _minimal_git_repo_with_config(tmp_path)
    req = WorkflowRunRequest.model_validate(
        {
            "workflow_path": str(wf),
            "agents_path": str(ag),
            "prompt": "",
            "repo_path": str(tmp_path),
        }
    )
    assert len(req.prompt) >= 5
    assert "Esplora la codebase" in req.prompt


def test_empty_workflow_path_uses_field_default(tmp_path: Path) -> None:
    _, ag = _minimal_git_repo_with_config(tmp_path)
    # Override only workflow to ensure the default relative path exists.
    (tmp_path / "config" / "workflow.yaml").write_text(
        "entry: alpha\nnodes: []\n", encoding="utf-8"
    )

    old_cwd = Path.cwd()
    try:
        # For defaults like "config/workflow.yaml", cwd must be the repo root.
        import os

        os.chdir(tmp_path)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": "",
                "agents_path": str(ag),
                "prompt": "hello world",
                "repo_path": str(tmp_path),
            }
        )
    finally:
        import os

        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_none_workflow_path_uses_field_default(tmp_path: Path) -> None:
    _, ag = _minimal_git_repo_with_config(tmp_path)
    (tmp_path / "config" / "workflow.yaml").write_text(
        "entry: alpha\nnodes: []\n", encoding="utf-8"
    )

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": None,
                "agents_path": str(ag),
                "prompt": "hello world",
                "repo_path": str(tmp_path),
            }
        )
    finally:
        import os

        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_accepts_testdata_yaml_paths(tmp_path: Path) -> None:
    import shutil

    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    wf = config_dir / "workflow.yaml"
    ag = config_dir / "agents.yaml"
    shutil.copy2(TESTDATA / "workflow.yaml", wf)
    shutil.copy2(TESTDATA / "agents.yaml", ag)

    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
        repo_path=str(tmp_path),
    )
    assert Path(req.workflow_path).name == "workflow.yaml"
    assert Path(req.agents_path).name == "agents.yaml"
