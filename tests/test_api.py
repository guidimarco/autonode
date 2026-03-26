from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autonode.application.use_cases.run_workflow_uc import RunWorkflowUseCaseResponse
from autonode.core.agents.models import ReviewVerdictModel
from autonode.presentation.api import app


def _success_response() -> RunWorkflowUseCaseResponse:
    return RunWorkflowUseCaseResponse(
        session_id="sid-1",
        branch_name="autonode/session-sid-1",
        verdict="approved",
        review_verdict=ReviewVerdictModel(
            is_approved=True,
            feedback="ok",
            missing_requirements=[],
        ),
        iteration=1,
        final_output="done",
        last_commit_hash="abc",
    )


def _stub_container() -> SimpleNamespace:
    # API unit tests only require `run_workflow_use_case`.
    return SimpleNamespace(run_workflow_use_case=MagicMock())


def test_execute_unauthorized_without_matching_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONODE_API_KEY", "secret")
    app.state.container = _stub_container()
    client = TestClient(app)
    response = client.post(
        "/execute",
        json={
            "prompt": "hello world",
            "repo_path": "/repo",
        },
    )
    assert response.status_code == 401


def test_execute_maps_payload_and_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONODE_API_KEY", "secret")
    app.state.container = _stub_container()
    client = TestClient(app)
    with patch(
        "autonode.presentation.api.run_autonode_workflow",
        return_value=_success_response(),
    ) as mock_run:
        response = client.post(
            "/execute",
            headers={"X-API-Key": "secret"},
            json={
                "prompt": "hello world",
                "repo_path": "/repo",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "sid-1"
    assert payload["branch_name"] == "autonode/session-sid-1"
    assert payload["verdict"] == "approved"
    assert payload["final_output"] == "done"
    mock_run.assert_called_once()
    raw = mock_run.call_args[0][1]
    assert raw["prompt"] == "hello world"
    assert raw["repo_path"] == "/repo"
    uuid.UUID(raw["thread_id"])


def test_execute_runtime_error_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONODE_API_KEY", "secret")
    app.state.container = _stub_container()
    client = TestClient(app)
    with patch(
        "autonode.presentation.api.run_autonode_workflow",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            "/execute",
            headers={"X-API-Key": "secret"},
            json={
                "prompt": "hello world",
                "repo_path": "/repo",
            },
        )
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal Server Error"
