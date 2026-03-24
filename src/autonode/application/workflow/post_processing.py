"""
Allowlisted actions executed after the LangGraph run completes.

Security: only registered handlers run; unknown `action` raises ValueError.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from autonode.core.workflow.models import PostProcessStepModel

logger = logging.getLogger(__name__)

PostHandler = Callable[[Mapping[str, Any], dict[str, Any]], dict[str, Any]]


def _action_noop(_state: Mapping[str, Any], _params: dict[str, Any]) -> dict[str, Any]:
    return {"action": "noop"}


def _action_log(_state: Mapping[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    msg = str(params.get("message", "post_processing"))
    level_name = str(params.get("level", "INFO")).upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.INFO
    logger.log(level, "[post_processing] %s", msg)
    return {"action": "log", "message": msg}


def _action_echo_state(state: Mapping[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    keys = params.get("keys")
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        keys = ["review_verdict", "iteration", "current_node"]
    values = {k: state.get(k) for k in keys}
    logger.info("[post_processing] echo_state %s", values)
    return {"action": "echo_state", "values": values}


_POST_HANDLERS: dict[str, PostHandler] = {
    "noop": _action_noop,
    "log": _action_log,
    "echo_state": _action_echo_state,
}


def run_post_processing(
    steps: list[PostProcessStepModel],
    final_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """
    Run configured steps in order. Each step must use an allowlisted `action` name.

    Args:
        steps: From WorkflowConfig.post_processing.
        final_state: Snapshot returned by graph.invoke (read-only convention).

    Returns:
        One result dict per step (for logging, API responses, or future persistence).
    """
    results: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        handler = _POST_HANDLERS.get(step.action)
        if handler is None:
            allowed = ", ".join(sorted(_POST_HANDLERS))
            raise ValueError(
                f"post_processing[{i}]: azione {step.action!r} non consentita. "
                f"Consentite: {allowed}"
            )
        results.append(handler(final_state, dict(step.params)))
    return results


def registered_post_actions() -> frozenset[str]:
    """Names exposed for config validation or docs."""
    return frozenset(_POST_HANDLERS)
