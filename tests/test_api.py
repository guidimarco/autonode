from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autonode.presentation.api import app


def _stub_container() -> SimpleNamespace:
    return SimpleNamespace(run_workflow_use_case=MagicMock())


@pytest.fixture
def repo_under_fake_src(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Repo Git minimale sotto un REPOS_ROOT fittizio (stessi vincoli di produzione)."""
    fake_src = tmp_path / "src"
    fake_src.mkdir()
    fake_data = tmp_path / "data"
    fake_data.mkdir()
    monkeypatch.setattr("autonode.core.sandbox.session_paths.REPOS_ROOT", str(fake_src))
    monkeypatch.setattr("autonode.core.sandbox.session_paths.DATA_ROOT", str(fake_data))
    repo = fake_src / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return "repo"


def test_execute_unauthorized_without_matching_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONODE_API_KEY", "secret")
    app.state.container = _stub_container()
    client = TestClient(app)
    response = client.post(
        "/execute",
        json={
            "prompt": "hello world",
            "repo_path": "repo",
        },
    )
    assert response.status_code == 401


def test_execute_returns_202_and_schedules_background(
    monkeypatch: pytest.MonkeyPatch,
    repo_under_fake_src: str,
) -> None:
    monkeypatch.setenv("AUTONODE_API_KEY", "secret")
    app.state.container = _stub_container()
    client = TestClient(app)
    with patch("autonode.presentation.api._execute_workflow_background") as bg:
        response = client.post(
            "/execute",
            headers={"X-API-Key": "secret"},
            json={
                "prompt": "hello world",
                "repo_path": repo_under_fake_src,
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert "session_id" in payload
    uuid.UUID(payload["session_id"])
    bg.assert_called_once()
    call = bg.call_args[0]
    assert call[0] is app.state.container
    raw = call[1]
    assert raw["prompt"] == "hello world"
    assert raw["thread_id"] == payload["session_id"]
    resolved_repo = Path(raw["repo_path"]).resolve()
    assert resolved_repo.name == "repo"
