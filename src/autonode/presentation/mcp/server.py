"""
FastMCP server for Autonode (stdio): wires the real workflow handler behind ``run_workflow``.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Repo .env before autonode imports so OPEN_ROUTER_API_KEY etc. are visible at import time.
_REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(_REPO_ROOT / ".env")

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from autonode.core.logging import LoggerFactory
from autonode.presentation.mcp.models import (
    RunWorkflowMcpToolResult,
    mcp_result_from_error,
    mcp_result_from_use_case,
    mcp_result_from_validation_error,
)
from autonode.presentation.mcp.stdio_safe import (
    configure_mcp_stdio_logging,
    isolate_process_stdout_to_stderr,
)
from autonode.presentation.workflow.handlers import run_workflow as run_autonode_workflow


def _default_workflow_path() -> str:
    return str(_REPO_ROOT / "config" / "workflow.yaml")


def _default_agents_path() -> str:
    return str(_REPO_ROOT / "config" / "agents.yaml")


mcp = FastMCP("Autonode", json_response=True)


def _raw_request_for_handler(
    *,
    prompt: str,
    repo_path: str,
    workflow_file: str,
    agents_file: str,
    thread_id: str,
) -> dict[str, Any]:
    """Map MCP tool args to ``WorkflowRunRequest`` (empty path → project config under repo root)."""
    wf = workflow_file.strip() or _default_workflow_path()
    af = agents_file.strip() or _default_agents_path()
    return {
        "prompt": prompt,
        "repo_path": repo_path,
        "thread_id": thread_id,
        "workflow_path": wf,
        "agents_path": af,
    }


def _execute_run_workflow_mcp(
    prompt: str,
    repo_path: str,
    workflow_file: str,
    agents_file: str,
) -> RunWorkflowMcpToolResult:
    log = LoggerFactory.get_logger()
    thread_id = str(uuid.uuid4())
    raw = _raw_request_for_handler(
        prompt=prompt,
        repo_path=repo_path,
        workflow_file=workflow_file,
        agents_file=agents_file,
        thread_id=thread_id,
    )
    log.info("MCP run_workflow start session_id=%s repo=%s", thread_id, repo_path)
    try:
        with isolate_process_stdout_to_stderr():
            response = run_autonode_workflow(raw)
        out = mcp_result_from_use_case(response)
        log.info(
            "MCP run_workflow done session_id=%s branch=%s",
            out["session_id"],
            out["branch_name"],
        )
        return out
    except ValidationError as exc:
        log.warning("MCP run_workflow validation error: %s", exc)
        return mcp_result_from_validation_error(exc)
    except Exception as exc:
        log.exception("MCP run_workflow failed")
        dbg = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)
        return mcp_result_from_error(exc, include_traceback=dbg)


@mcp.tool()
def run_workflow(
    prompt: str,
    repo_path: str,
    workflow_file: str = "",
    agents_file: str = "",
) -> RunWorkflowMcpToolResult:
    """
    Run an Autonode multi-agent workflow in an isolated worktree and Docker sandbox.

    Returns branch name and a short summary of the last agent output. Empty YAML path strings
    resolve to ``config/workflow.yaml`` and ``config/agents.yaml`` under the Autonode package repo.
    """
    return _execute_run_workflow_mcp(
        prompt=prompt,
        repo_path=repo_path,
        workflow_file=workflow_file,
        agents_file=agents_file,
    )


def run_mcp_server() -> None:
    """Start the MCP server on stdio (JSON-RPC over stdin/stdout)."""
    level_name = os.environ.get("AUTONODE_MCP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    configure_mcp_stdio_logging(level=level)
    mcp.run(transport="stdio")
