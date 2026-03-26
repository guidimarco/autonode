"""
CLI entry point: loads workflow + agents from disk, runs graph, then post_processing.
"""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv
from pydantic import ValidationError

from autonode.bootstrap import AppContainer, bootstrap_app
from autonode.core.logging import LoggerFactory
from autonode.infrastructure.logging.stderr_adapter import install_autonode_process_logging
from autonode.presentation.cleanup.handlers import run_cleanup
from autonode.presentation.workflow.handlers import run_workflow

load_dotenv()


def main() -> None:
    """
    CLI entry point.

    Subcommands:
      cleanup   - remove orphaned worktrees / containers
      (default) - run the multi-agent workflow

    To start the unified API+MCP server use ``presentation.server`` directly.
    """
    install_autonode_process_logging(level=logging.INFO)

    container = bootstrap_app()

    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        _run_cleanup_cli(container, sys.argv[2:])
        return

    _run_workflow_cli(container, sys.argv[1:])


# ── Run workflow CLI ───────────────────────────────────────────────────────


def _run_workflow_cli(container: AppContainer, args_list: list[str]) -> None:
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

    raw = {
        "prompt": parser.parse_args(args_list).prompt,
        "repo_path": parser.parse_args(args_list).repo,
        "workflow_path": parser.parse_args(args_list).workflow,
        "agents_path": parser.parse_args(args_list).agents,
    }

    try:
        log.info("Running workflow...")
        result = run_workflow(container.run_workflow_use_case, raw)
        log.info("Workflow finished successfully: %s", result)
    except ValidationError as exc:
        log.error("Validation error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        log.error("Unexpected error: %s", exc)
        sys.exit(1)


# ── Run cleanup CLI ───────────────────────────────────────────────────────


def _run_cleanup_cli(container: AppContainer, args_list: list[str]) -> None:
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

    raw = {
        "repo_path": parser.parse_args(args_list).repo_path,
        "session_id": parser.parse_args(args_list).session_id,
        "delete_branch": parser.parse_args(args_list).delete_branch,
    }

    try:
        run_cleanup(container.cleanup_use_case, raw)
        log.info("Cleanup completed")
    except ValidationError as e:
        log.error("Validation error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
