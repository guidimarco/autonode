"""
CLI entry point: loads workflow + agents from disk, runs graph, then post_processing.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from autonode.application.graph import build_graph
from autonode.application.post_processing import run_post_processing
from autonode.application.workflow_state import make_initial_graph_state
from autonode.infrastructure import CrewFactory, configure_tracing
from autonode.infrastructure.config.loader import load_workflow_config
from autonode.infrastructure.sandbox.docker_adapter import DockerAdapter
from autonode.infrastructure.tools.registry import ToolRegistry
from autonode.infrastructure.vcs.git_worktree_provider import GitWorktreeProvider
from autonode.infrastructure.vcs.workspace_cleanup import (
    cleanup_all_session_worktrees,
    cleanup_orphaned_worktrees,
)
from autonode.presentation.models import WorkflowRunRequest

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def _run_cleanup_cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="autonode cleanup")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help=(
            "Rimuove tutti i worktree sotto .autonode/worktrees/ "
            "e tutti i container autonode-sandbox-*"
        ),
    )
    group.add_argument(
        "--prune",
        action="store_true",
        help="Rimuove solo worktree e container sandbox più vecchi di 24 ore",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Root del repository (directory che contiene .git)",
    )
    args = parser.parse_args(argv)

    if args.all:
        removed_wt = cleanup_all_session_worktrees(args.repo)
        logger.info("Worktree rimossi (%d): %s", len(removed_wt), removed_wt)
        try:
            docker = DockerAdapter(prepare_image=False)
            removed_c = docker.remove_autonode_sandboxes()
            logger.info("Container rimossi (%d): %s", len(removed_c), removed_c)
        except Exception as e:
            logger.warning("Pulizia Docker non eseguita: %s", e)
        return

    removed_wt = cleanup_orphaned_worktrees(args.repo, ttl_days=1)
    logger.info("Worktree orfani rimossi (%d): %s", len(removed_wt), removed_wt)
    try:
        docker = DockerAdapter(prepare_image=False)
        removed_c = docker.remove_stale_autonode_sandboxes(ttl_days=1.0)
        logger.info("Container sandbox obsoleti rimossi (%d): %s", len(removed_c), removed_c)
    except Exception as e:
        logger.warning("Prune Docker non eseguito: %s", e)


def main() -> None:
    """
    Run workflow: un solo percorso — worktree Git → container Docker → grafo → cleanup.

    Non esiste esecuzione “solo locale”: senza worktree e container la CLI termina in errore.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        _run_cleanup_cli(sys.argv[2:])
        return

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
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Non rimuovere il container sandbox a fine run (debug)",
    )

    try:
        args = parser.parse_args()
        request = WorkflowRunRequest(
            workflow_path=args.workflow,
            agents_path=args.agents,
            prompt=args.prompt,
        )
    except ValidationError as e:
        logger.error("Validation error: %s", e)
        return

    repo_path = str(Path(args.repo).resolve())
    if not Path(repo_path).is_dir():
        logger.critical("Percorso --repo non è una directory: %s", repo_path)
        sys.exit(1)

    configure_tracing()

    workflow = load_workflow_config(request.workflow_path)

    thread_id = str(uuid.uuid4())
    logger.info("Starting task | thread_id=%s | workflow=%s", thread_id, request.workflow_path)

    vcs = GitWorktreeProvider()
    try:
        sandbox = DockerAdapter()
        workspace = vcs.setup_session_worktree(thread_id, repo_path)
        execution_env = sandbox.provision_environment(workspace)
    except Exception as e:
        logger.critical("Provisioning fallito (Git worktree o Docker): %s", e, exc_info=True)
        sys.exit(1)

    registry = ToolRegistry(execution_env=execution_env)
    factory = CrewFactory(
        config_path=request.agents_path,
        tool_registry=registry,
    )
    graph = build_graph(workflow, factory, registry, vcs_provider=vcs)

    initial_state = make_initial_graph_state(
        request.prompt,
        execution_env=execution_env,
        workspace=workspace,
    )

    try:
        final_state = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )
    finally:
        if not args.no_cleanup:
            sandbox.release_environment(execution_env)

    post_results = run_post_processing(workflow.post_processing, final_state)

    last_msg = final_state["messages"][-1]
    print("\n─── Risultato finale ───────────────────────────────────────────")
    print(f"Verdict  : {final_state['verdict']}")
    print(f"Iteration: {final_state['iteration']}")
    print(f"Output   :\n{getattr(last_msg, 'content', last_msg)}")
    if post_results:
        print(f"Post     : {post_results}")
    print("────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
