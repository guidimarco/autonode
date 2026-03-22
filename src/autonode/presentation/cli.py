"""
CLI entry point: loads workflow + agents from disk, runs graph, then post_processing.
"""

from __future__ import annotations

import argparse
import logging
import uuid

from dotenv import load_dotenv
from pydantic import ValidationError

from autonode.application.graph import build_graph
from autonode.application.post_processing import run_post_processing
from autonode.application.workflow_state import make_initial_graph_state
from autonode.infrastructure import CrewFactory, ToolRegistry, configure_tracing
from autonode.infrastructure.workflow_loader import load_workflow_config
from autonode.presentation.models import WorkflowRunRequest

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
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

    configure_tracing()

    workflow = load_workflow_config(request.workflow_path)
    registry = ToolRegistry(root_dir="./src/autonode")
    factory = CrewFactory(config_path=request.agents_path, tool_registry=registry)
    graph = build_graph(workflow, factory, registry)

    thread_id = str(uuid.uuid4())
    logger.info("Starting task | thread_id=%s | workflow=%s", thread_id, request.workflow_path)

    final_state = graph.invoke(
        make_initial_graph_state(request.prompt),
        config={"configurable": {"thread_id": thread_id}},
    )

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
