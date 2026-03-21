"""
CLI entry point: wires infrastructure to application and runs the LangGraph workflow.
"""

import logging
import uuid

from dotenv import load_dotenv

from autonode.application.graph import build_graph, make_initial_state
from autonode.infrastructure import CrewFactory, ToolRegistry, configure_tracing

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    configure_tracing()

    registry = ToolRegistry(root_dir="./playground")
    factory = CrewFactory(config_path="config/agents.yaml", tool_registry=registry)
    graph = build_graph(factory, registry)

    prompt = "Crea un file fibonacci.py con una funzione che calcoli i primi N numeri di Fibonacci."
    thread_id = str(uuid.uuid4())
    logger.info("Avvio task | thread_id=%s", thread_id)

    final_state = graph.invoke(
        make_initial_state(prompt),
        config={"configurable": {"thread_id": thread_id}},
    )

    last_msg = final_state["messages"][-1]
    print("\n─── Risultato finale ───────────────────────────────────────────")
    print(f"Verdict  : {final_state['verdict']}")
    print(f"Iteration: {final_state['iteration']}")
    print(f"Output   :\n{getattr(last_msg, 'content', last_msg)}")
    print("────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
