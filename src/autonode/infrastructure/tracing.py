"""
LangSmith tracing configuration.

Call configure_tracing() once at application startup (before any LLM call).
All LangChain/LangGraph runs are automatically captured when tracing is enabled.

Required env vars (see .env.example):
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=ls__...
    LANGCHAIN_PROJECT=autonode   (optional, default: "default")
"""

import logging
import os

logger = logging.getLogger(__name__)


def configure_tracing() -> bool:
    """
    Activate LangSmith tracing from environment variables.

    Returns True if tracing is active, False otherwise.
    LangChain reads LANGCHAIN_TRACING_V2 / LANGCHAIN_API_KEY natively;
    this function validates the config and logs the effective state so there
    are no silent misconfigurations.
    """
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

    if not tracing_enabled:
        logger.info("LangSmith tracing disabled (LANGCHAIN_TRACING_V2 != true)")
        return False

    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    if not api_key:
        logger.warning(
            "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY is not set — "
            "tracing will fail. Set the key or disable tracing."
        )
        return False

    project = os.getenv("LANGCHAIN_PROJECT", "default")
    endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    logger.info(
        "LangSmith tracing active | project=%s | endpoint=%s",
        project,
        endpoint,
    )
    return True


def get_run_metadata(task_id: str | None = None) -> dict[str, str]:
    """
    Return a metadata dict to pass to LangChain/LangGraph invoke calls.
    Adds a 'task_id' tag so runs are groupable in the LangSmith dashboard.

    Usage:
        graph.invoke(state, config={"metadata": get_run_metadata(task_id="abc")})
    """
    meta: dict[str, str] = {
        "project": os.getenv("LANGCHAIN_PROJECT", "autonode"),
    }
    if task_id:
        meta["task_id"] = task_id
    return meta
