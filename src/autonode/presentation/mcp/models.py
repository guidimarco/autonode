"""MCP presentation types and response mapping for the ``run_workflow`` tool."""

from __future__ import annotations

import traceback
from typing import Literal, TypedDict

from pydantic import ValidationError

from autonode.application.use_cases.run_workflow_uc import RunWorkflowUseCaseResponse

_SUMMARY_MAX_LEN = 4000


class RunWorkflowMcpToolResult(TypedDict):
    """Structured tool result returned to MCP clients (also mirrored as JSON text when needed)."""

    status: Literal["success", "error"]
    branch_name: str
    summary: str
    session_id: str


def summarize_final_output(text: str, *, max_len: int = _SUMMARY_MAX_LEN) -> str:
    """Concise summary for mobile/desktop UIs: strip and cap length."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 3]}..."


def mcp_result_from_use_case(response: RunWorkflowUseCaseResponse) -> RunWorkflowMcpToolResult:
    return {
        "status": "success",
        "branch_name": response.branch_name,
        "summary": summarize_final_output(response.final_output),
        "session_id": response.session_id,
    }


def mcp_result_from_validation_error(exc: ValidationError) -> RunWorkflowMcpToolResult:
    parts: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "")
        parts.append(f"{loc}: {msg}".strip())
    message = "; ".join(parts) if parts else str(exc)
    return {
        "status": "error",
        "branch_name": "",
        "summary": summarize_final_output(message, max_len=_SUMMARY_MAX_LEN),
        "session_id": "",
    }


def mcp_result_from_error(
    exc: BaseException,
    *,
    include_traceback: bool,
) -> RunWorkflowMcpToolResult:
    if include_traceback:
        tb = traceback.format_exc()
        body = f"{type(exc).__name__}: {exc}\n{tb}"
    else:
        body = f"{type(exc).__name__}: {exc}"
    return {
        "status": "error",
        "branch_name": "",
        "summary": summarize_final_output(body, max_len=_SUMMARY_MAX_LEN),
        "session_id": "",
    }
