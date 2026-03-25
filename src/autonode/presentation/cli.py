"""
CLI entry point: loads workflow + agents from disk, runs graph, then post_processing.
"""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv
from pydantic import ValidationError

from autonode.core.logging import LoggerFactory
from autonode.infrastructure.logging.stderr_adapter import install_autonode_process_logging
from autonode.presentation.cleanup.handlers import run_cleanup
from autonode.presentation.workflow.handlers import run_workflow

load_dotenv()


def main() -> None:
    """
    CLI entry point.
    """
    install_autonode_process_logging(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        _run_cleanup_cli(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        _run_mcp_cli(sys.argv[2:])
        return

    _run_workflow_cli(sys.argv[1:])


# ── Run workflow CLI ───────────────────────────────────────────────────────


def _run_workflow_cli(args_list: list[str]) -> None:
    log = LoggerFactory.get_logger()
    parser = argparse.ArgumentParser(description="Autonode: multi-agent workflow (LangGraph)")
    parser.add_argument(
        "--workflow",
        help="Path al YAML di workflow (topologia grafo)",
    )
    parser.add_argument(
        "--agents",
        help="Path al catalogo agenti",
    )
    parser.add_argument(
        "--prompt",
        help="Task testuale per l'agente",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Root del repository Git (directory che contiene .git); usato per worktree e sandbox",
    )

    try:
        run_workflow_response = run_workflow(parser.parse_args(args_list).__dict__)
        log.info(
            "> Sandbox pulita. Modifiche conservate nel branch: %s",
            run_workflow_response.branch_name,
        )
    except ValidationError as e:
        log.error("Validation error: %s", e)
        sys.exit(1)


# ── MCP server CLI ─────────────────────────────────────────────────────────


def _run_mcp_cli(args_list: list[str]) -> None:
    """Start Model Context Protocol server (stdio). Extra args reserved for future use."""
    log = LoggerFactory.get_logger()
    if args_list:
        log.warning("Ignoring unused MCP CLI args: %s", args_list)
    from autonode.presentation.mcp.server import run_mcp_server

    try:
        run_mcp_server()
    except KeyboardInterrupt:
        import os

        log.info("MCP server stopped by user")
        os._exit(0)
    except Exception as e:
        log.error("Error starting MCP server: %s", e)
        sys.exit(1)


# ── Run cleanup CLI ───────────────────────────────────────────────────────


def _run_cleanup_cli(args_list: list[str]) -> None:
    log = LoggerFactory.get_logger()
    parser = argparse.ArgumentParser(prog="autonode cleanup")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Root del repository Git (directory che contiene .git); usato per worktree e sandbox",
    )
    parser.add_argument(
        "--session-id",
        help="ID della sessione",
    )
    parser.add_argument(
        "--delete-branch",
        action="store_true",
        help="Rimuovere il branch dopo la pulizia",
    )
    args = parser.parse_args(args_list).__dict__

    try:
        run_cleanup(args)
        log.info("Cleanup completed")
    except ValidationError as e:
        log.error("Validation error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
