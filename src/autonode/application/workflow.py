"""
Workflow use case: run a multi-agent flow (coder → reviewer).
Depends on ports (tool registry, agent factory) for framework-agnostic orchestration.
"""

from collections.abc import Callable
from typing import Any


def execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    get_tool_fn: Callable[[str], Any],
    tool_message_factory: Callable[[str, str], Any],
) -> list[Any]:
    """
    Execute requested tools and return a list of tool result messages.
    get_tool_fn(name) returns the tool; tool.invoke(args) runs it.
    tool_message_factory(content, tool_call_id) builds the message to append.
    """
    responses = []
    for tool_call in tool_calls:
        name = tool_call["name"]
        args = tool_call.get("args", {})
        print(f"Richiesto tool: {name} con argomenti: {args}")
        tool = get_tool_fn(name)
        if tool is None:
            continue
        result = tool.invoke(args)
        msg = tool_message_factory(str(result), tool_call["id"])
        responses.append(msg)
    return responses


def run_workflow(
    prompt: str,
    *,
    create_agent_fn: Callable[[str], Any],
    get_tool_list_fn: Callable[[list[str]], list[Any]],
    message_types: Any,
) -> None:
    """
    Run the coder → reviewer workflow.
    create_agent_fn(agent_id) returns a runnable agent.
    get_tool_list_fn(names) returns list of tools for execution.
    message_types: namespace with HumanMessage, ToolMessage (LangChain).
    """
    HumanMessage = message_types.HumanMessage
    ToolMessage = message_types.ToolMessage

    def get_tool(name: str) -> Any:
        tools = get_tool_list_fn([name])
        return tools[0] if tools else None

    def make_tool_message(content: str, tool_call_id: str) -> Any:
        return ToolMessage(content, tool_call_id)

    coder = create_agent_fn("coder")
    reviewer = create_agent_fn("reviewer")

    print(f"🚀 Avvio workflow con prompt: {prompt}")

    messages = [HumanMessage(content=prompt)]
    # Step 1: Coder
    coder_response = coder.invoke(messages)
    messages.append(coder_response)
    if getattr(coder_response, "tool_calls", None):
        tool_results = execute_tool_calls(coder_response.tool_calls, get_tool, make_tool_message)
        messages.extend(tool_results)
        coder_response = coder.invoke(messages)
        messages.append(coder_response)
    print(f"🚀 Coder ha terminato: {coder_response.content}")

    # Step 2: Reviewer
    review_prompt = (
        f"Analizza il lavoro fatto. "
        f"Se ci sono modifiche, leggi il file e verifica che siano corrette. "
        f"Contesto: {coder_response.content}"
    )
    messages.append(HumanMessage(content=review_prompt))
    reviewer_response = reviewer.invoke(messages)
    messages.append(reviewer_response)
    if getattr(reviewer_response, "tool_calls", None):
        tool_results = execute_tool_calls(reviewer_response.tool_calls, get_tool, make_tool_message)
        messages.extend(tool_results)
        reviewer_response = reviewer.invoke(messages)
        messages.append(reviewer_response)
    print(f"🚀 Reviewer ha terminato: {reviewer_response.content}")
