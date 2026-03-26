from __future__ import annotations

import uuid

from mcp.server.fastmcp import FastMCP

from autonode.bootstrap import AppContainer
from autonode.core.logging import LoggerFactory
from autonode.presentation.mcp.models import (
    RunWorkflowMcpToolResult,
    mcp_result_from_error,
    mcp_result_from_use_case,
)
from autonode.presentation.mcp.stdio_safe import (
    configure_mcp_stdio_logging,
    isolate_process_stdout_to_stderr,
)
from autonode.presentation.workflow.handlers import run_workflow as run_autonode_workflow

log = LoggerFactory.get_logger()
mcp = FastMCP(name="Autonode", json_response=True)

_container: AppContainer | None = None

# --- Helpers ---


def _get_container() -> AppContainer:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container


# --- MCP server ---


def run_mcp_server(container: AppContainer, log_level: int) -> None:
    global _container
    _container = container

    configure_mcp_stdio_logging(level=log_level)

    log.info("MCP server started")

    mcp.run(transport="stdio")


# --- Tools ---


@mcp.tool()
def run_workflow(
    prompt: str,
    repo_path: str,
    workflow_path: str = "",
    agents_path: str = "",
) -> RunWorkflowMcpToolResult:
    """
    Run a workflow in the Docker sandbox.
    """

    container = _get_container()
    thread_id = str(uuid.uuid4())

    raw_request = {
        "thread_id": thread_id,
        "prompt": prompt,
        "repo_path": repo_path,
        "workflow_path": workflow_path or None,
        "agents_path": agents_path or None,
    }

    try:
        with isolate_process_stdout_to_stderr():
            response = run_autonode_workflow(container.run_workflow_use_case, raw_request)
            return mcp_result_from_use_case(response)
    except Exception as e:
        log.error("Error running workflow: %s", e)
        return mcp_result_from_error(e, include_traceback=False)
