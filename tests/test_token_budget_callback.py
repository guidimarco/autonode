"""Token budget LangChain callback (hard limit)."""

import pytest
from langchain_core.outputs import LLMResult

from autonode.infrastructure.telemetry.token_callback import (
    TokenBudgetCallback,
    TokenBudgetExceeded,
)


def _result(tokens: int) -> LLMResult:
    return LLMResult(
        generations=[],
        llm_output={"token_usage": {"total_tokens": tokens}},
    )


def test_zero_budget_is_unlimited() -> None:
    cb = TokenBudgetCallback(budget=0)
    cb.on_llm_end(_result(1_000_000))
    assert cb.total_tokens == 0


def test_accumulates_until_budget_then_raises() -> None:
    cb = TokenBudgetCallback(budget=100)
    cb.on_llm_end(_result(40))
    assert cb.total_tokens == 40
    cb.on_llm_end(_result(50))
    assert cb.total_tokens == 90
    with pytest.raises(TokenBudgetExceeded) as ei:
        cb.on_llm_end(_result(20))
    assert ei.value.total_tokens >= 100
    assert ei.value.budget == 100


def test_missing_token_usage_does_not_raise() -> None:
    cb = TokenBudgetCallback(budget=10)
    cb.on_llm_end(LLMResult(generations=[], llm_output=None))
    assert cb.total_tokens == 0
