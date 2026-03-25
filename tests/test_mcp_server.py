"""MCP presentation: response mapping and workflow tool wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from autonode.application.use_cases.run_workflow_uc import RunWorkflowUseCaseResponse
from autonode.core.agents.models import ReviewVerdictModel
from autonode.presentation.mcp.models import (
    RunWorkflowMcpToolResult,
    mcp_result_from_use_case,
    mcp_result_from_validation_error,
    summarize_final_output,
)
from autonode.presentation.mcp.server import _execute_run_workflow_mcp, _raw_request_for_handler
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


def test_raw_request_empty_strings_resolve_repo_config_paths() -> None:
    import autonode.presentation.mcp.server as server_mod

    root = Path(server_mod.__file__).resolve().parents[4]
    raw = _raw_request_for_handler(
        prompt="do thing",
        repo_path="/repo",
        workflow_file="",
        agents_file="",
        thread_id="tid-1",
    )
    assert raw == {
        "prompt": "do thing",
        "repo_path": "/repo",
        "thread_id": "tid-1",
        "workflow_path": str(root / "config" / "workflow.yaml"),
        "agents_path": str(root / "config" / "agents.yaml"),
    }


def test_raw_request_includes_explicit_optional_paths() -> None:
    raw = _raw_request_for_handler(
        prompt="p",
        repo_path="/r",
        workflow_file="/w.yaml",
        agents_file="/a.yaml",
        thread_id="tid-2",
    )
    assert raw["workflow_path"] == "/w.yaml"
    assert raw["agents_path"] == "/a.yaml"


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
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        return_value=uc_response,
    ) as mock_run:
        out = _execute_run_workflow_mcp("prompt text", "/repo", "", "")
    mock_run.assert_called_once()
    passed = mock_run.call_args[0][0]
    repo_root = Path(__file__).resolve().parents[1]
    assert passed["prompt"] == "prompt text"
    assert passed["repo_path"] == "/repo"
    assert passed["thread_id"]
    assert passed["workflow_path"] == str(repo_root / "config" / "workflow.yaml")
    assert passed["agents_path"] == str(repo_root / "config" / "agents.yaml")
    assert out["status"] == "success"
    assert out["branch_name"] == "autonode/session-s1"
    assert out["summary"] == "done"
    assert out["session_id"] == "s1"


def test_execute_run_workflow_mcp_validation_error() -> None:
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        side_effect=ValidationError.from_exception_data(
            "WorkflowRunRequest",
            [{"type": "missing", "loc": ("prompt",), "input": {}}],
        ),
    ):
        out = _execute_run_workflow_mcp("x", "/repo", "", "")
    assert out["status"] == "error"
    assert out["branch_name"] == ""
    assert "prompt" in out["summary"].lower() or "field" in out["summary"].lower()


def test_execute_run_workflow_mcp_runtime_error() -> None:
    with patch(
        "autonode.presentation.mcp.server.run_autonode_workflow",
        side_effect=RuntimeError("boom"),
    ):
        out = _execute_run_workflow_mcp("p", "/repo", "", "")
    assert out["status"] == "error"
    assert "RuntimeError" in out["summary"]
    assert "boom" in out["summary"]
