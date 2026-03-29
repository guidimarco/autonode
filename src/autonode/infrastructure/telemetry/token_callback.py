"""LLM callback: session-level token accounting and hard budget enforcement."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class TokenBudgetExceeded(Exception):
    """Raised when cumulative LLM token usage reaches or exceeds the configured budget."""

    def __init__(self, total_tokens: int, budget: int) -> None:
        self.total_tokens = total_tokens
        self.budget = budget
        super().__init__(f"Token budget exceeded: total_tokens={total_tokens} budget={budget}")


def _total_tokens_from_llm_result(response: LLMResult) -> int:
    """Best-effort extraction; providers may omit token_usage (returns 0)."""
    out = response.llm_output
    if not isinstance(out, dict):
        return 0
    usage = out.get("token_usage")
    if not isinstance(usage, dict):
        return 0
    raw = usage.get("total_tokens")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return 0
    return max(raw, 0)


class TokenBudgetCallback(BaseCallbackHandler):
    """Accumulates reported token usage and raises when the hard cap is reached."""

    def __init__(self, budget: int) -> None:
        super().__init__()
        self._budget = budget
        self.total_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        # budget <= 0 means unlimited (see core.constants.DEFAULT_TOKEN_BUDGET).
        if self._budget <= 0:
            return
        self.total_tokens += _total_tokens_from_llm_result(response)
        if self.total_tokens >= self._budget:
            raise TokenBudgetExceeded(self.total_tokens, self._budget)
