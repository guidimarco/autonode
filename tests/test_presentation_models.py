"""Test del modello Pydantic `WorkflowRunRequest` (presentation layer)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autonode.presentation.workflow.models import WorkflowRunRequest

TESTDATA = Path(__file__).resolve().parent / "testdata"

# Minimal valid workflow V2 for path-existence checks (matches WorkflowYamlSchema).
_MINIMAL_WORKFLOW_V2 = """\
version: 2
factory: dev_review_loop
max_iterations: 3
token_budget: 1000
agents_path: config/agents.yaml
"""


@pytest.fixture
def fake_repos_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Simula ``REPOS_ROOT`` (es. ``/src`` in container) sotto ``tmp_path``."""
    r = tmp_path / "src"
    r.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.REPOS_ROOT", str(r))
    return r


def _minimal_git_repo_with_config(repo_root: Path) -> tuple[Path, Path]:
    """
    Create a minimal git repo root for validation:
    - ``repo_root/.git/`` exists (repo_path validator)
    - ``repo_root/config/`` contains workflow + agents YAMLs (config-only validator)
    """
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    workflow = config_dir / "workflow.yaml"
    agents = config_dir / "agents.yaml"
    workflow.write_text(_MINIMAL_WORKFLOW_V2, encoding="utf-8")
    agents.write_text("agents: []\n", encoding="utf-8")
    return workflow, agents


def test_accepts_existing_paths(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    wf, ag = _minimal_git_repo_with_config(repo_root)
    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
        repo_path=str(repo_root),
    )
    assert req.workflow_path == str(wf)
    assert req.agents_path == str(ag)
    assert req.prompt == "hello world"


def test_rejects_missing_workflow_path(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    _, ag = _minimal_git_repo_with_config(repo_root)
    missing_wf = repo_root / "config" / "nope.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(missing_wf),
            agents_path=str(ag),
            prompt="hello world",
            repo_path=str(repo_root),
        )


def test_rejects_missing_agents_path(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    wf, _ = _minimal_git_repo_with_config(repo_root)
    missing_ag = repo_root / "config" / "nope_agents.yaml"
    with pytest.raises(ValueError, match="does not exist"):
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(missing_ag),
            prompt="hello world",
            repo_path=str(repo_root),
        )


def test_prompt_too_short_raises(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    wf, ag = _minimal_git_repo_with_config(repo_root)
    with pytest.raises(ValidationError) as exc:
        WorkflowRunRequest(
            workflow_path=str(wf),
            agents_path=str(ag),
            prompt="1234",
            repo_path=str(repo_root),
        )
    errs = exc.value.errors()
    assert any(e.get("type") == "string_too_short" and e.get("loc") == ("prompt",) for e in errs)


def test_empty_prompt_uses_default(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    wf, ag = _minimal_git_repo_with_config(repo_root)
    req = WorkflowRunRequest.model_validate(
        {
            "workflow_path": str(wf),
            "agents_path": str(ag),
            "prompt": "",
            "repo_path": str(repo_root),
        }
    )
    assert len(req.prompt) >= 5
    assert "Esplora la codebase" in req.prompt


def test_empty_workflow_path_uses_field_default(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    _, ag = _minimal_git_repo_with_config(repo_root)
    (repo_root / "config" / "workflow.yaml").write_text(_MINIMAL_WORKFLOW_V2, encoding="utf-8")

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(repo_root)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": "",
                "agents_path": str(ag),
                "prompt": "hello world",
                "repo_path": str(repo_root),
            }
        )
    finally:
        import os

        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_none_workflow_path_uses_field_default(fake_repos_root: Path) -> None:
    repo_root = fake_repos_root / "proj"
    _, ag = _minimal_git_repo_with_config(repo_root)
    (repo_root / "config" / "workflow.yaml").write_text(_MINIMAL_WORKFLOW_V2, encoding="utf-8")

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(repo_root)
        req = WorkflowRunRequest.model_validate(
            {
                "workflow_path": None,
                "agents_path": str(ag),
                "prompt": "hello world",
                "repo_path": str(repo_root),
            }
        )
    finally:
        import os

        os.chdir(old_cwd)
    assert req.workflow_path == "config/workflow.yaml"


def test_accepts_testdata_yaml_paths(fake_repos_root: Path) -> None:
    import shutil

    repo_root = fake_repos_root / "proj"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    config_dir = repo_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    wf = config_dir / "workflow.yaml"
    ag = config_dir / "agents.yaml"
    shutil.copy2(TESTDATA / "workflow_default.yaml", wf)
    shutil.copy2(TESTDATA / "agents.yaml", ag)

    req = WorkflowRunRequest(
        workflow_path=str(wf),
        agents_path=str(ag),
        prompt="hello world",
        repo_path=str(repo_root),
    )
    assert Path(req.workflow_path).name == "workflow.yaml"
    assert Path(req.agents_path).name == "agents.yaml"
