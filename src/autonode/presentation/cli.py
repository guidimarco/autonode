"""
CLI entry point: wires infrastructure to application and runs the workflow.
"""

from types import SimpleNamespace

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from autonode.application.workflow import run_workflow
from autonode.infrastructure import CrewFactory, ToolRegistry

load_dotenv()


def _create_message_types() -> SimpleNamespace:
    return SimpleNamespace(
        HumanMessage=HumanMessage,
        AIMessage=AIMessage,
        ToolMessage=ToolMessage,
    )


def main() -> None:
    registry = ToolRegistry(root_dir="./playground")
    factory = CrewFactory(config_path="config/agents.yaml", tool_registry=registry)
    message_types = _create_message_types()

    run_workflow(
        "Crea un file app.py con una funzione che calcoli la frequenza di fibonacci",
        create_agent_fn=factory.create_agent,
        get_tool_list_fn=registry.get_tool_list,
        message_types=message_types,
    )


if __name__ == "__main__":
    main()
