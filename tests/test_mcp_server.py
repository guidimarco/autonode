"""MCP presentation: response mapping and workflow tool wiring."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import autonode.presentation.mcp.server as server_mod
from autonode.application.use_cases.run_workflow_uc import RunWorkflowUseCaseResponse
from autonode.bootstrap import AppContainer
from autonode.core.agents.models import ReviewVerdictModel
from autonode.presentation.mcp.models import (
    RunWorkflowMcpToolResult,
    mcp_result_from_use_case,
    mcp_result_from_validation_error,
    summarize_final_output,
)
from autonode.presentation.workflow.models import WorkflowRunRequest


def test_summarize_final_output_truncates() -> None:
    long = "x" * 5000
    out = summarize_final_output(long, max_len=100)
    assert len(out) == 100
    assert out.endswith("...")


def test_mcp_result_from_use_case_maps_fields() -> None:
    rv = ReviewVerdictModel(is_approved=True, feedback="", missing_requirements=[])
    response = RunWorkflowUseCaseResponse(
        session_id="sid-9",
        branch_name="autonode/session-x",
        verdict="approved",
        review_verdict=rv,
        iteration=2,
        final_output="  hello\nworld  ",
        last_commit_hash="deadbeef",
    )
    result = mcp_result_from_use_case(response)
    assert result == RunWorkflowMcpToolResult(
        status="success",
        branch_name="autonode/session-x",
        summary="hello world",
        session_id="sid-9",
    )


def test_mcp_result_from_validation_error() -> None:
    with pytest.raises(ValidationError) as excinfo:
        WorkflowRunRequest.model_validate(
            {
                "workflow_path": "/nope/not-there.yaml",
                "agents_path": "/nope/agents.yaml",
                "prompt": "hello world",
            }
        )
    err = excinfo.value
    result = mcp_result_from_validation_error(err)
    assert result["status"] == "error"
    assert result["branch_name"] == ""
    assert result["session_id"] == ""
    assert "does not exist" in result["summary"]


def test_execute_run_workflow_mcp_success() -> None:
    rv = ReviewVerdictModel(is_approved=True, feedback="", missing_requirements=[])
    uc_response = RunWorkflowUseCaseResponse(
        session_id="s1",
        branch_name="autonode/session-s1",
        verdict="approved",
        review_verdict=rv,
        iteration=0,
        final_output="done",
        last_commit_hash="abc",
    )

    server_mod._container = cast(AppContainer, SimpleNamespace(run_workflow_use_case=MagicMock()))
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        return_value=uc_response,
    ) as mock_run:
        out = server_mod.run_workflow(
            prompt="prompt text", repo_path="/repo", workflow_path="", agents_path=""
        )

    mock_run.assert_called_once()
    passed_raw = mock_run.call_args[0][1]
    uuid.UUID(passed_raw["thread_id"])
    assert passed_raw["prompt"] == "prompt text"
    assert passed_raw["repo_path"] == "/repo"
    assert passed_raw["workflow_path"] is None
    assert passed_raw["agents_path"] is None

    assert out["status"] == "success"
    assert out["branch_name"] == "autonode/session-s1"
    assert out["summary"] == "done"
    assert out["session_id"] == "s1"


def test_execute_run_workflow_mcp_validation_error() -> None:
    server_mod._container = cast(AppContainer, SimpleNamespace(run_workflow_use_case=MagicMock()))
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        side_effect=ValidationError.from_exception_data(
            "WorkflowRunRequest",
            [{"type": "missing", "loc": ("prompt",), "input": {}}],
        ),
    ):
        out = server_mod.run_workflow(
            prompt="x", repo_path="/repo", workflow_path="", agents_path=""
        )

    assert out["status"] == "error"
    assert out["branch_name"] == ""
    assert "ValidationError" in out["summary"]


def test_execute_run_workflow_mcp_runtime_error() -> None:
    server_mod._container = cast(AppContainer, SimpleNamespace(run_workflow_use_case=MagicMock()))
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        side_effect=RuntimeError("boom"),
    ):
        out = server_mod.run_workflow(
            prompt="p", repo_path="/repo", workflow_path="", agents_path=""
        )

    assert out["status"] == "error"
    assert "RuntimeError" in out["summary"]
    assert "boom" in out["summary"]
